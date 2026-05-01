"""
chat_history.py
Menyimpan dan mengambil riwayat chat dari Qdrant.
Kompatibel untuk lokal dan Streamlit Cloud.
"""

import os
import time
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue, PayloadSchemaType
)
from dotenv import load_dotenv

load_dotenv()

CHAT_COLLECTION = "chat_history"
MAX_HISTORY = 6  # 3 percakapan = 6 pesan


def get_client() -> QdrantClient:
    # Lazy-load agar secrets_loader sempat inject env vars lebih dulu
    return QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
        timeout=60
    )


def ensure_collection():
    """Buat collection + index jika belum ada."""
    client = get_client()
    existing = [c.name for c in client.get_collections().collections]
    if CHAT_COLLECTION not in existing:
        client.create_collection(
            collection_name=CHAT_COLLECTION,
            vectors_config=VectorParams(size=1, distance=Distance.COSINE),
        )
    # Pastikan index ada (idempotent)
    try:
        client.create_payload_index(
            collection_name=CHAT_COLLECTION,
            field_name="session_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
    except Exception:
        pass  # Index sudah ada


def save_message(session_id: str, role: str, content: str):
    """Simpan satu pesan ke Qdrant."""
    try:
        ensure_collection()
        client = get_client()
        int_id = int(time.time() * 1000) % (2**53)
        client.upsert(
            collection_name=CHAT_COLLECTION,
            points=[PointStruct(
                id=int_id,
                vector=[0.0],
                payload={
                    "session_id": session_id,
                    "role": role,
                    "content": content,
                    "timestamp": time.time(),
                }
            )]
        )
    except Exception as e:
        print(f"Warning: Gagal simpan chat history: {e}")


def load_history(session_id: str) -> list[dict]:
    """Ambil riwayat chat dari Qdrant untuk session tertentu."""
    try:
        ensure_collection()
        client = get_client()
        results, _ = client.scroll(
            collection_name=CHAT_COLLECTION,
            scroll_filter=Filter(
                must=[FieldCondition(
                    key="session_id",
                    match=MatchValue(value=session_id)
                )]
            ),
            limit=100,
            with_payload=True,
            with_vectors=False,
        )
        messages = sorted(
            [r.payload for r in results],
            key=lambda x: x.get("timestamp", 0)
        )
        return [{"role": m["role"], "content": m["content"]} for m in messages[-MAX_HISTORY:]]
    except Exception as e:
        print(f"Warning: Gagal load chat history: {e}")
        return []


def list_sessions() -> list[dict]:
    """
    Ambil semua session yang ada beserta pesan pertama user sebagai preview.
    Return: [{"session_id": ..., "preview": ..., "timestamp": ...}]
    """
    try:
        ensure_collection()
        client = get_client()
        results, _ = client.scroll(
            collection_name=CHAT_COLLECTION,
            limit=500,
            with_payload=True,
            with_vectors=False,
        )
        # Kelompokkan per session_id
        sessions = {}
        for r in results:
            sid = r.payload.get("session_id")
            ts = r.payload.get("timestamp", 0)
            role = r.payload.get("role")
            content = r.payload.get("content", "")
            if sid not in sessions:
                sessions[sid] = {"session_id": sid, "preview": "", "timestamp": 0}
            # Ambil pesan user pertama sebagai preview
            if role == "user" and ts < sessions[sid]["timestamp"] or sessions[sid]["preview"] == "":
                if role == "user":
                    sessions[sid]["preview"] = content[:50] + ("..." if len(content) > 50 else "")
            # Simpan timestamp terbaru
            if ts > sessions[sid]["timestamp"]:
                sessions[sid]["timestamp"] = ts

        # Urutkan dari terbaru
        return sorted(sessions.values(), key=lambda x: x["timestamp"], reverse=True)
    except Exception as e:
        print(f"Warning: Gagal load sessions: {e}")
        return []


def clear_history(session_id: str):
    """Hapus semua pesan untuk session tertentu."""
    try:
        client = get_client()
        client.delete(
            collection_name=CHAT_COLLECTION,
            points_selector=Filter(
                must=[FieldCondition(
                    key="session_id",
                    match=MatchValue(value=session_id)
                )]
            ),
        )
    except Exception as e:
        print(f"Warning: Gagal hapus chat history: {e}")
