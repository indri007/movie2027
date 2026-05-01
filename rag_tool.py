"""
rag_tool.py
RAG (Retrieval-Augmented Generation) tool untuk mengambil informasi
dari Qdrant vector database berdasarkan query pengguna.
"""

import os
from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "personal_assistant")
EMBEDDING_MODEL = "text-embedding-3-small"
TOP_K = 3  # Jumlah dokumen yang diambil

# Gunakan OpenAIEmbeddings dari langchain_openai
embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)


def embed_query(query: str) -> list[float]:
    """Menghasilkan embedding vector dari query menggunakan OpenAI via LangChain."""
    return embeddings.embed_query(query)


@tool
def rag_search(query: str) -> str:
    """
    Mencari informasi relevan dari knowledge base (vector database) berdasarkan query.
    Gunakan tool ini untuk menjawab pertanyaan tentang fitur asisten, cara penggunaan,
    atau informasi umum yang tersimpan di knowledge base.
    """
    try:
        qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=30)
        query_vector = embed_query(query)

        results = qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=TOP_K,
            with_payload=True,
        )

        if not results:
            return "❌ Tidak ditemukan informasi relevan di knowledge base."

        output = f"📚 Informasi relevan untuk '{query}':\n\n"
        for i, hit in enumerate(results, 1):
            score = round(hit.score, 3)
            text = hit.payload.get("text", "")
            category = hit.payload.get("category", "")
            output += f"{i}. [{category.upper()}] (skor: {score})\n{text}\n\n"

        return output.strip()
    except Exception as e:
        return f"❌ Gagal mengakses knowledge base: {str(e)}"
