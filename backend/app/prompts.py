SYSTEM_PROMPT = """Kamu adalah asisten data analyst penerbitan buku. Gunakan hanya data dalam konteks.
Data berisi penjualan per judul buku dalam satuan juta (penjualan (juta)), beserta penulis, bahasa, tahun terbit, dan genre.
Selalu mulai dengan headline insight, sebut angka dengan konteks, dan akhiri dengan rekomendasi actionable.
Gunakan bahasa Indonesia. Jangan mengarang fakta atau angka di luar DATA KONTEKS dan STATISTIK TERPERCAYA.
Jika konteks tidak memuat jawaban untuk pertanyaan, katakan terus terang bahwa datanya tidak tersedia dan sarankan pertanyaan lain; jangan mengarang.
Balas JSON valid dengan keys narration, chart, recommendation. chart boleh null; jika ada harus bertipe bar, line, atau pie, memiliki key labels dan datasets, jumlah labels sama dengan jumlah data tiap dataset, dan semua nilai data berupa angka non-negatif.
"""

MAX_HISTORY_TURNS = 6
MAX_TURN_CHARS = 600

def build_prompt(question: str, context: str, stats: dict, history: list[dict] | None = None) -> str:
    riwayat = ""
    if history:
        lines = "\n".join(
            f"{turn.get('role', 'user')}: {str(turn.get('content', ''))[:MAX_TURN_CHARS]}"
            for turn in history[-MAX_HISTORY_TURNS:]
        )
        riwayat = f"\nRIWAYAT PERCAKAPAN SEBELUMNYA (user = pertanyaan, assistant = jawabanmu):\n{lines}\n"
    return f"""{SYSTEM_PROMPT}\n{riwayat}\nDATA KONTEKS:\n{context}\n\nSTATISTIK TERPERCAYA:\n{stats}\n\nPERTANYAAN:\n{question}\n"""
