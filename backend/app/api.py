import csv
import io
import json
import re
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from .config import settings
from .db import connect
from .domain import REQUIRED_COLUMNS
from .prompts import build_prompt
from .schemas import ChatRequest, ChatResponse
from .vector import index_rows

router = APIRouter()
SESSIONS: dict[str, tuple[datetime, list[dict]]] = {}

@router.get("/template/csv")
def template_csv():
    body = "judul_buku,penulis,bahasa,tahun,penjualan (juta),genre\nLaskar Pelangi,Andrea Hirata,Indonesia,2005,8.5,Sastra\n"
    return StreamingResponse(io.BytesIO(body.encode()), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=template.csv"})

def _parse_rows(content: bytes):
    try:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
    except UnicodeDecodeError as exc:
        raise HTTPException(422, "CSV harus menggunakan encoding UTF-8") from exc
    missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
    if missing:
        raise HTTPException(422, f"Kolom {', '.join(missing)} tidak ditemukan. Pastikan format CSV sesuai template.")
    rows, errors = [], []
    for line, row in enumerate(reader, start=2):
        try:
            values = {key: (row.get(key) or "").strip() for key in REQUIRED_COLUMNS}
            parsed = (values["judul_buku"], values["penulis"], values["bahasa"], int(values["tahun"]), float(values["penjualan (juta)"]), values["genre"])
            if not all(parsed[:3]) or not parsed[5]: raise ValueError("nilai wajib kosong")
            if parsed[3] <= 0 or parsed[4] <= 0: raise ValueError("tahun atau penjualan tidak valid")
            rows.append(parsed)
        except (ValueError, TypeError) as exc:
            errors.append(f"Baris {line}: {exc}")
    return rows, errors

@router.post("/upload/csv")
async def upload_csv(file: UploadFile = File(...)):
    rows, errors = _parse_rows(await file.read())
    if not rows:
        raise HTTPException(422, {"message": "Tidak ada baris valid", "errors": errors})
    connection = connect()
    try:
        connection.execute("DELETE FROM sales_transactions")
        connection.executemany("INSERT INTO sales_transactions (judul_buku, penulis, bahasa, tahun, penjualan_juta, genre) VALUES (?, ?, ?, ?, ?, ?)", rows)
        connection.execute("DELETE FROM books")
        connection.execute("""INSERT INTO books SELECT judul_buku, penulis, bahasa, MAX(tahun), SUM(penjualan_juta), MAX(genre) FROM sales_transactions GROUP BY judul_buku""")
        status = "partial" if errors else "success"
        cursor = connection.execute("INSERT INTO ingest_records (filename, created_at, successful_rows, failed_rows, status) VALUES (?, ?, ?, ?, ?)", (file.filename or "upload.csv", datetime.now(timezone.utc).isoformat(), len(rows), len(errors), status))
        connection.commit()
        index_rows(rows)
        return {"filename": file.filename, "successful_rows": len(rows), "failed_rows": len(errors), "errors": errors, "status": status, "ingest_id": cursor.lastrowid}
    finally:
        connection.close()

@router.get("/ingests")
def ingests():
    connection = connect()
    try: return [dict(row) for row in connection.execute("SELECT * FROM ingest_records ORDER BY id DESC")]
    finally: connection.close()

_STOP_WORDS = {"apa", "yang", "paling", "laris", "berapa", "bagaimana", "tren", "bandingkan", "genre", "buku", "dari", "dan", "di", "ke", "dengan", "untuk", "pada", "ini", "itu", "ada", "bulan", "tahun", "selama", "antara", "penulis", "bahasa", "penjualan"}
_ASCENDING_WORDS = ("terkecil", "terendah", "terbawah", "minimal", "paling sedikit", "sedikit", "tersedikit")
def _search(message: str):
    connection = connect()
    try:
        lower = message.lower()
        ascending = any(word in lower for word in _ASCENDING_WORDS)
        order = "ASC" if ascending else "DESC"
        terms = [term for term in re.findall(r"[\w-]+", message.lower()) if len(term) > 2 and term not in _STOP_WORDS]
        clauses, params = [], []
        for term in terms[:8]:
            clauses.append("(lower(judul_buku) LIKE ? OR lower(genre) LIKE ? OR lower(penulis) LIKE ? OR lower(bahasa) LIKE ?)")
            params.extend([f"%{term}%"] * 4)
        where = " OR ".join(clauses) if clauses else None
        stats = dict(connection.execute("SELECT COUNT(*) total_buku, COALESCE(SUM(penjualan_juta),0) total_penjualan_juta, COALESCE(AVG(penjualan_juta),0) rata_rata FROM books").fetchone())
        if where:
            rows = connection.execute(f"SELECT * FROM books WHERE {where} ORDER BY penjualan_juta {order} LIMIT 20", params).fetchall()
            per_genre = connection.execute(f"SELECT genre, SUM(penjualan_juta) penjualan, COUNT(*) total_buku FROM books WHERE {where} GROUP BY genre ORDER BY penjualan {order}", params).fetchall()
        else:
            rows = connection.execute(f"SELECT * FROM books ORDER BY penjualan_juta {order} LIMIT 20").fetchall()
            per_genre = connection.execute(f"SELECT genre, SUM(penjualan_juta) penjualan, COUNT(*) total_buku FROM books GROUP BY genre ORDER BY penjualan {order}").fetchall()
        if not rows and stats["total_buku"] > 0:
            rows = connection.execute(f"SELECT * FROM books ORDER BY penjualan_juta {order} LIMIT 20").fetchall()
            per_genre = connection.execute(f"SELECT genre, SUM(penjualan_juta) penjualan, COUNT(*) total_buku FROM books GROUP BY genre ORDER BY penjualan {order}").fetchall()
        per_penulis = connection.execute(f"SELECT penulis, SUM(penjualan_juta) penjualan, COUNT(*) total_buku FROM books GROUP BY penulis ORDER BY penjualan {order} LIMIT 10").fetchall()
        return rows, stats, [dict(row) for row in per_genre], [dict(row) for row in per_penulis], ascending
    finally: connection.close()

def _fallback(stats):
    return {"narration": f"**Total penjualan tercatat {stats['total_penjualan_juta']:g} juta untuk {stats['total_buku']} buku.**\n\nRata-rata penjualan per buku {stats['rata_rata']:g} juta.", "chart": None, "recommendation": "Gunakan pertanyaan yang lebih spesifik untuk menemukan buku atau genre unggulan.", "mode": "local-fallback"}

def _ask_deepseek(question: str, context: str, stats: dict):
    if not settings.deepseek_api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.deepseek_api_key, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(model=settings.deepseek_model, messages=[{"role": "user", "content": build_prompt(question, context, stats)}], response_format={"type": "json_object"}, timeout=60)
        result = json.loads(response.choices[0].message.content or "{}")
        chart = result.get("chart")
        if chart is not None and (chart.get("type") not in {"bar", "line", "pie"} or len(chart.get("labels", [])) != len(chart.get("datasets", [{}])[0].get("data", []))):
            chart = None
        return {"narration": str(result.get("narration", "")), "chart": chart, "recommendation": result.get("recommendation"), "mode": "deepseek"}
    except Exception:
        return None

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    rows, stats, per_genre, per_penulis, ascending = _search(request.message)
    if not rows or stats["total_buku"] == 0:
        result = {"narration": "Data penjualan tidak cukup untuk menjawab pertanyaan ini. Coba pertanyaan yang lebih spesifik.", "chart": None, "recommendation": None, "mode": "empty"}
    else:
        context = "\n".join(f"{row['judul_buku']} — {row['penulis']} — {row['genre']} — bahasa {row['bahasa']} — tahun {row['tahun']} — penjualan {row['penjualan_juta']:g} juta" for row in rows)
        if per_genre:
            summary = "\n".join(f"{g['genre']}: {g['penjualan']:g} juta dari {g['total_buku']} buku" for g in per_genre)
            context += f"\n\nRINGKASAN PER GENRE:\n{summary}"
        if per_penulis:
            label = "TERKECIL" if ascending else "TERBESAR"
            summary_penulis = "\n".join(f"{p['penulis']}: {p['penjualan']:g} juta dari {p['total_buku']} buku" for p in per_penulis)
            context += f"\n\nRINGKASAN PER PENULIS ({label}):\n{summary_penulis}"
        result = _ask_deepseek(request.message, context, stats) or _fallback(stats)
        if request.session_id not in SESSIONS or datetime.now(timezone.utc) - SESSIONS[request.session_id][0] > timedelta(hours=1): SESSIONS[request.session_id] = (datetime.now(timezone.utc), [])
        SESSIONS[request.session_id][1].append({"role": "user", "content": request.message})
        result["sources"] = [str(row["judul_buku"]) for row in rows]
    if "sources" not in result: result["sources"] = []
    return result

@router.get("/sessions/{session_id}/history")
def history(session_id: str):
    session = SESSIONS.get(session_id)
    if not session or datetime.now(timezone.utc) - session[0] > timedelta(hours=1): return []
    return session[1]
