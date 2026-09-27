import io, json, pytest
from fastapi.testclient import TestClient
from app.api import _parse_rows, _search
from app.db import SCHEMA, connect
from app.config import settings
from app import main
from app import api as api_mod

TEST_DB = "data/test_sales.db"

def _test_connect():
    import sqlite3
    from pathlib import Path
    path = Path(TEST_DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn

class TestCsvParsing:
    valid_csv = b"judul_buku,penulis,bahasa,tahun,penjualan (juta),genre\nLaskar Pelangi,Andrea Hirata,Indonesia,2005,8.5,Sastra"
    missing_header = b"judul_buku,penulis,bahasa\nLaskar,AH,Indonesia"
    bad_tahun = b"judul_buku,penulis,bahasa,tahun,penjualan (juta),genre\nLaskar,AH,Indonesia,abc,8.5,Sastra"
    zero_penjualan = b"judul_buku,penulis,bahasa,tahun,penjualan (juta),genre\nLaskar,AH,Indonesia,2005,0,Sastra"
    extra_lines = b"judul_buku,penulis,bahasa,tahun,penjualan (juta),genre\nLaskar,AH,Indonesia,2005,8.5,Sastra\nBumi,Pram,Indonesia,1980,7.2,Fiksi\nBroken,,Indonesia,1990,abc,Sastra"
    empty_keyword = b"judul_buku,penulis,bahasa,tahun,penjualan (juta),genre\n,The Alchemist,Portugis,1988,a,Fiksi\n..."

    def test_valid_all_rows(self):
        rows, errors = _parse_rows(TestCsvParsing.valid_csv)
        assert len(rows) == 1
        assert errors == []
        assert rows[0][0] == "Laskar Pelangi"

    def test_invalid_empty_csv(self):
        with pytest.raises(Exception):
            _parse_rows(b"")

    def test_valid_tahun_parsing(self):
        rows, _ = _parse_rows(TestCsvParsing.valid_csv)
        assert rows[0][3] == 2005

    def test_missing_and_optional_columns(self):
        with pytest.raises(Exception):
            _parse_rows(TestCsvParsing.missing_header)

    def test_numeric_enforcement(self):
        rows, errors = _parse_rows(TestCsvParsing.zero_penjualan)
        assert rows == []
        assert len(errors) == 1

    def test_partial_with_errors(self):
        rows, errors = _parse_rows(TestCsvParsing.extra_lines)
        assert len(rows) >= 1
        assert len(errors) > 0

    def test_price_string_rejection(self):
        rows, errors = _parse_rows(TestCsvParsing.empty_keyword)
        assert len(errors) > 0 or len(rows) == 0

    def test_keyword_search_stops_terms(self):
        assert "laris" in api_mod._STOP_WORDS
        assert "genre" in api_mod._STOP_WORDS


class TestDomainAndSchema:
    def test_required_columns(self):
        from app.domain import REQUIRED_COLUMNS
        assert "judul_buku" in REQUIRED_COLUMNS
        assert "penjualan (juta)" in REQUIRED_COLUMNS

    def test_schema_execution(self):
        conn = _test_connect()
        columns = conn.execute("PRAGMA table_info(sales_transactions)").fetchall()
        names = {col["name"] for col in columns}
        assert "judul_buku" in names
        assert "penjualan_juta" in names

    def test_books_table_derived(self):
        conn = _test_connect()
        columns = conn.execute("PRAGMA table_info(books)").fetchall()
        names = {col["name"] for col in columns}
        assert "penjualan_juta" in names

    def test_ingest_records_table(self):
        conn = _test_connect()
        before = conn.execute("SELECT COUNT(*) c FROM ingest_records").fetchone()["c"]
        conn.execute("INSERT INTO ingest_records (filename, created_at, successful_rows, failed_rows, status) VALUES ('test.csv', 'now', 5, 0, 'success')")
        conn.commit()
        after = conn.execute("SELECT COUNT(*) c FROM ingest_records").fetchone()["c"]
        assert after == before + 1


class TestIntegrationViaClient:
    sample_csv = b"judul_buku,penulis,bahasa,tahun,penjualan (juta),genre\nLaskar Pelangi,Andrea Hirata,Indonesia,2005,8.5,Sastra\nBumi Manusia,Pramoedya Ananta Toer,Indonesia,1980,7.2,Fiksi"

    @pytest.fixture
    def client(self, monkeypatch):
        """Test client yang tidak menimpa database production."""
        monkeypatch.setattr(settings, "database_path", TEST_DB)
        monkeypatch.setattr(settings, "deepseek_api_key", "")
        return TestClient(main.app)

    def test_template_download(self, client):
        response = client.get("/api/template/csv")
        assert response.status_code == 200
        assert "penjualan (juta)" in response.text

    def test_upload_valid_csv(self, client):
        response = client.post("/api/upload/csv", files={"file": ("sample.csv", TestIntegrationViaClient.sample_csv, "text/csv")})
        assert response.status_code == 200
        data = response.json()
        assert data["successful_rows"] == 2
        assert data["status"] == "success"
        assert data["ingest_id"] is not None

    def test_upload_bad_csv(self, client):
        response = client.post("/api/upload/csv", files={"file": ("bad.csv", b"wrong,columns,only\n1,2,3", "text/csv")})
        assert response.status_code == 422

    def test_upload_empty_csv(self, client):
        response = client.post("/api/upload/csv", files={"file": ("empty.csv", b"", "text/csv")})
        assert response.status_code == 422

    def test_chat_empty_no_data(self, client):
        response = client.post("/api/chat", json={"message": "Apa saja?", "session_id": "no-data"})
        assert response.status_code == 200
        data = response.json()
        assert "narration" in data
        assert "mode" in data

    def test_chat_after_upload(self, client):
        client.post("/api/upload/csv", files={"file": ("sample.csv", TestIntegrationViaClient.sample_csv, "text/csv")})
        response = client.post("/api/chat", json={"message": "Laskar Pelangi", "session_id": "has-data"})
        data = response.json()
        assert response.status_code == 200
        assert data["mode"] != "empty"

    def test_ingest_history(self, client):
        resp = client.get("/api/ingests")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_session_empty(self, client):
        resp = client.get("/api/sessions/nonexistent/history")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_chart_mapping(self, client):
        """Kirim pertanyaan lalu verifikasi struktur response lengkap."""
        client.post("/api/upload/csv", files={"file": ("sample.csv", TestIntegrationViaClient.sample_csv, "text/csv")})
        response = client.post("/api/chat", json={"message": "Laskar Pelangi Sastra", "session_id": "schema"})
        data = response.json()
        assert "narration" in data
        assert "chart" in data
        assert "sources" in data
        assert "mode" in data

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.json() == {"status": "ok"}
