import sqlite3
from pathlib import Path
from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS sales_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, judul_buku TEXT NOT NULL, penulis TEXT NOT NULL, bahasa TEXT NOT NULL, tahun INTEGER NOT NULL, penjualan_juta REAL NOT NULL, genre TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS books (judul_buku TEXT PRIMARY KEY, penulis TEXT NOT NULL, bahasa TEXT NOT NULL, tahun INTEGER NOT NULL, penjualan_juta REAL NOT NULL, genre TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ingest_records (id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT NOT NULL, created_at TEXT NOT NULL, successful_rows INTEGER NOT NULL, failed_rows INTEGER NOT NULL, status TEXT NOT NULL);
"""

def connect() -> sqlite3.Connection:
    path = Path(settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.executescript(SCHEMA)
    return connection
