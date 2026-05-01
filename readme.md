# 🤖 Personal AI Assistant - Capstone Project Module 3

Multi-agent AI assistant berbasis LangGraph dengan supervisor pattern, terintegrasi dengan cuaca, film (IMDb), Gmail, Google Calendar, dan RAG knowledge base.

## Arsitektur

```
User (Streamlit UI)
        │
        ▼
  Supervisor Agent  ◄──── RAG Tool (Qdrant)
   /      |      \
  ▼       ▼       ▼
Weather  IMDB   Gmail/Calendar
 Agent   Agent    Agent
  │       │         │
  ▼       ▼         ▼
OpenWeather OMDB  Google API
  API     API   (Gmail + Calendar)
```

## Struktur File

```
├── app.py                  # Streamlit UI
├── superviser_workflow.py  # Supervisor multi-agent workflow
├── weather_agent.py        # Agent cuaca (OpenWeatherMap)
├── imdb_agent.py           # Agent film/serial (OMDB/IMDb)
├── gmail_agent.py          # Agent Gmail & Google Calendar
├── rag_tool.py             # RAG tool (Qdrant vector search)
├── vector_db.py            # Setup & populate Qdrant database
├── requirements.txt        # Dependencies
└── .env.example            # Template environment variables
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Konfigurasi Environment

Salin `.env.example` ke `.env` dan isi semua nilai:

```bash
cp .env.example .env
```

```env
OPENAI_API_KEY=your_openai_api_key
OPENWEATHER_API_KEY=your_openweather_api_key
OMDB_API_KEY=your_omdb_api_key
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_COLLECTION=personal_assistant
GMAIL_CREDENTIALS_PATH=credentials.json
GMAIL_TOKEN_PATH=token.json
```

### 3. Setup Google API (Gmail & Calendar)

1. Buka [Google Cloud Console](https://console.cloud.google.com)
2. Buat project baru atau pilih yang sudah ada
3. Aktifkan **Gmail API** dan **Google Calendar API**
4. Buat OAuth 2.0 credentials (Desktop App)
5. Download `credentials.json` dan letakkan di root project
6. Jalankan sekali untuk autentikasi: `python gmail_agent.py`

### 4. Setup Qdrant Cloud

1. Daftar di [Qdrant Cloud](https://cloud.qdrant.io)
2. Buat cluster baru
3. Salin URL dan API key ke `.env`
4. Jalankan setup vector database:

```bash
python vector_db.py
```

### 5. Jalankan Aplikasi

```bash
streamlit run app.py
```

## Cara Penggunaan

Contoh perintah yang bisa digunakan:

| Kategori | Contoh Perintah |
|----------|----------------|
| Cuaca | "Bagaimana cuaca di Jakarta hari ini?" |
| Film | "Cari info film Inception" |
| Film | "Tampilkan film action terbaik 2023" |
| Email | "Kirim email ke user@example.com dengan subjek 'Meeting' dan isi 'Besok jam 10'" |
| Email | "Baca 3 email terbaru saya" |
| Kalender | "Buat acara rapat besok jam 14:00 sampai 15:00" |
| Kalender | "Tampilkan acara mendatang saya" |
| Gabungan | "Cek cuaca Jakarta lalu kirim hasilnya ke user@example.com" |
| Knowledge | "Apa saja fitur asisten ini?" |

## Komponen Penilaian

- ✅ **Vector Database**: `vector_db.py` - setup Qdrant dengan embedding OpenAI
- ✅ **RAG Tool**: `rag_tool.py` - embed query + retrieve dari Qdrant
- ✅ **Multi-Agent**: supervisor + 3 agent spesialis (weather, imdb, gmail)
- ✅ **Chat History**: disimpan di Streamlit session state, 3 percakapan terakhir
- ✅ **Streamlit UI**: `app.py` dengan sidebar, contoh pertanyaan, dan chat interface
