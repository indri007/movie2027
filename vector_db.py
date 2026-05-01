"""
vector_db.py
Membuat dan mengisi Qdrant vector database dengan data pengetahuan umum
sebagai sumber informasi untuk RAG tool.
"""

import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from openai import OpenAI

load_dotenv()

# === Konfigurasi ===
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "personal_assistant")
EMBEDDING_MODEL = "text-embedding-3-small"
VECTOR_SIZE = 1536

# === Data Pengetahuan (dokumen yang akan di-embed) ===
DOCUMENTS = [
    {
        "id": 1,
        "text": "Asisten pribadi ini dapat membantu Anda mengecek cuaca terkini di berbagai kota di seluruh dunia menggunakan data real-time dari OpenWeatherMap.",
        "metadata": {"category": "weather", "topic": "fitur cuaca"}
    },
    {
        "id": 2,
        "text": "Untuk informasi film dan serial TV, asisten ini menggunakan database OMDB yang mencakup judul, sutradara, pemain, rating IMDb, tahun rilis, dan sinopsis.",
        "metadata": {"category": "imdb", "topic": "fitur film"}
    },
    {
        "id": 3,
        "text": "Asisten dapat mengirim email melalui akun Gmail Anda menggunakan Google Gmail API dengan autentikasi OAuth2 yang aman.",
        "metadata": {"category": "gmail", "topic": "fitur email"}
    },
    {
        "id": 4,
        "text": "Fitur kalender memungkinkan Anda membuat, melihat, dan mengelola acara di Google Calendar langsung melalui percakapan dengan asisten.",
        "metadata": {"category": "calendar", "topic": "fitur kalender"}
    },
    {
        "id": 5,
        "text": "Asisten pribadi ini dibangun menggunakan arsitektur multi-agent dengan LangGraph dan LangChain. Supervisor agent mendelegasikan tugas ke agent spesialis: weather agent, IMDB agent, dan Gmail/Calendar agent.",
        "metadata": {"category": "system", "topic": "arsitektur sistem"}
    },
    {
        "id": 6,
        "text": "Cara menggunakan asisten: cukup ketik pertanyaan atau perintah dalam bahasa natural. Contoh: 'Bagaimana cuaca di Jakarta hari ini?', 'Cari informasi film Inception', 'Kirim email ke tim tentang meeting besok'.",
        "metadata": {"category": "system", "topic": "cara penggunaan"}
    },
    {
        "id": 7,
        "text": "Rating IMDb adalah sistem penilaian film dari 1 hingga 10 berdasarkan voting pengguna. Film dengan rating di atas 8.0 dianggap sangat bagus. The Shawshank Redemption memiliki rating tertinggi 9.3.",
        "metadata": {"category": "imdb", "topic": "rating imdb"}
    },
    {
        "id": 8,
        "text": "Cuaca dipengaruhi oleh berbagai faktor seperti suhu, kelembaban, tekanan udara, dan kecepatan angin. Suhu diukur dalam Celsius (°C) atau Fahrenheit (°F).",
        "metadata": {"category": "weather", "topic": "pengetahuan cuaca"}
    },
    {
        "id": 9,
        "text": "Google Calendar mendukung pembuatan acara berulang, pengingat, undangan tamu, dan integrasi dengan Google Meet untuk video conference.",
        "metadata": {"category": "calendar", "topic": "fitur google calendar"}
    },
    {
        "id": 10,
        "text": "Gmail adalah layanan email dari Google yang mendukung label, filter, pencarian canggih, dan integrasi dengan berbagai aplikasi Google Workspace.",
        "metadata": {"category": "gmail", "topic": "fitur gmail"}
    },
]


def get_embedding(text: str, client: OpenAI) -> list[float]:
    """Menghasilkan embedding vector dari teks menggunakan OpenAI."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding


def setup_vector_db():
    """Membuat collection dan mengisi Qdrant dengan dokumen yang sudah di-embed."""
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=60)

    # Buat collection jika belum ada
    existing = [c.name for c in qdrant_client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        print(f"✅ Collection '{COLLECTION_NAME}' berhasil dibuat.")
    else:
        print(f"ℹ️  Collection '{COLLECTION_NAME}' sudah ada.")

    # Embed dan insert dokumen satu per satu
    count = 0
    for doc in DOCUMENTS:
        print(f"  Memproses dokumen {doc['id']}...")
        vector = get_embedding(doc["text"], openai_client)
        point = PointStruct(
            id=doc["id"],
            vector=vector,
            payload={"text": doc["text"], **doc["metadata"]}
        )
        qdrant_client.upsert(collection_name=COLLECTION_NAME, points=[point])
        count += 1

    print(f"✅ {count} dokumen berhasil dimasukkan ke vector database.")


if __name__ == "__main__":
    setup_vector_db()
