from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal

REQUIRED_COLUMNS = ("judul_buku", "penulis", "bahasa", "tahun", "penjualan (juta)", "genre")

@dataclass(frozen=True)
class Sale:
    judul_buku: str
    penulis: str
    bahasa: str
    tahun: int
    penjualan_juta: float
    genre: str

@dataclass(frozen=True)
class ParsedRows:
    rows: list[Sale]
    errors: list[str]

@dataclass(frozen=True)
class IngestResult:
    filename: str
    successful_rows: int
    failed_rows: int
    errors: list[str]
    status: Literal["success", "partial", "failed"]
    ingest_id: int | None = None

@dataclass(frozen=True)
class Evidence:
    id: str
    text: str
    metadata: dict[str, Any]
    score: float = 0.0

@dataclass(frozen=True)
class RetrievalResult:
    question: str
    evidence: list[Evidence]
    stats: dict[str, Any]
    mode: Literal["semantic", "keyword", "empty"]
    has_sufficient_data: bool

@dataclass(frozen=True)
class StoryResponse:
    narration: str
    chart: dict[str, Any] | None
    recommendation: str | None
    mode: str
    sources: list[str]

@dataclass(frozen=True)
class IngestRecord:
    id: int
    filename: str
    created_at: datetime
    successful_rows: int
    failed_rows: int
    status: str
