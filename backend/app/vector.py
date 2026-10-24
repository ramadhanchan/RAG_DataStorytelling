import logging
from .config import settings

logger = logging.getLogger(__name__)

_model = None
_collection = None
_unavailable = False

def _resources():
    global _model, _collection, _unavailable
    if not settings.vector_enabled:
        raise RuntimeError("vector store dinonaktifkan via VECTOR_ENABLED")
    if _unavailable:
        raise RuntimeError("vector store tidak tersedia")
    try:
        if _collection is None:
            import chromadb
            client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
            _collection = client.get_or_create_collection("sales_chunks")
        if _model is None:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(settings.embedding_model, device="cpu")
    except Exception:
        _unavailable = True
        raise
    return _model, _collection

def index_rows(rows):
    if not rows or not settings.vector_enabled:
        return
    try:
        model, collection = _resources()
        documents = [f"{row[0]} — {row[1]} — genre {row[5]} — bahasa {row[2]} — tahun {row[3]} — penjualan {row[4]:g} juta" for row in rows]
        embeddings = model.encode(documents, normalize_embeddings=True).tolist()
        collection.upsert(ids=[f"transaction-{row[0]}-{row[3]}" for row in rows], documents=documents, embeddings=embeddings, metadatas=[{"judul_buku": row[0], "genre": row[5], "tahun": row[3]} for row in rows])
    except Exception as exc:
        logger.warning("Indexing vektor gagal (data tetap tersimpan di SQLite): %s", exc)

def search(question: str, limit: int = 8):
    if not settings.vector_enabled:
        return []
    try:
        model, collection = _resources()
        vector = model.encode([question], normalize_embeddings=True).tolist()
        result = collection.query(query_embeddings=vector, n_results=limit)
        return [{"text": text, "metadata": metadata, "score": 1 - distance} for text, metadata, distance in zip(result["documents"][0], result["metadatas"][0], result["distances"][0])]
    except Exception as exc:
        logger.warning("Vector search gagal, lanjut ke SQL keyword: %s", exc)
        return []
