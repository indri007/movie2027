"""
imdb_agent.py
Agent spesialis untuk mencari informasi film dan serial TV via OMDB API (data IMDb).
"""

import os
import requests
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

load_dotenv()

# === LLM ===
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.1,
    max_tokens=800,
)


@tool
def search_movie(title: str) -> str:
    """
    Mencari informasi film atau serial TV berdasarkan judul.
    Mengembalikan detail seperti sutradara, pemain, rating IMDb, tahun, dan sinopsis.
    """
    api_key = os.getenv("OMDB_API_KEY")
    if not api_key:
        return "❌ OMDB_API_KEY tidak ditemukan di environment."

    url = f"http://www.omdbapi.com/?t={requests.utils.quote(title)}&apikey={api_key}&plot=short"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("Response") == "False":
            return f"❌ Film '{title}' tidak ditemukan. Coba judul yang lebih spesifik."

        return (
            f"🎬 {data.get('Title', 'N/A')} ({data.get('Year', 'N/A')})\n"
            f"- Genre: {data.get('Genre', 'N/A')}\n"
            f"- Sutradara: {data.get('Director', 'N/A')}\n"
            f"- Pemain: {data.get('Actors', 'N/A')}\n"
            f"- Rating IMDb: {data.get('imdbRating', 'N/A')}/10\n"
            f"- Durasi: {data.get('Runtime', 'N/A')}\n"
            f"- Bahasa: {data.get('Language', 'N/A')}\n"
            f"- Sinopsis: {data.get('Plot', 'N/A')}"
        )
    except requests.RequestException as e:
        return f"❌ Gagal mengambil data film: {str(e)}"


@tool
def search_movies_by_keyword(keyword: str, year: str = "") -> str:
    """
    Mencari daftar film berdasarkan kata kunci.
    Parameter year (opsional) untuk memfilter berdasarkan tahun.
    Mengembalikan daftar film yang cocok.
    """
    api_key = os.getenv("OMDB_API_KEY")
    if not api_key:
        return "❌ OMDB_API_KEY tidak ditemukan di environment."

    url = f"http://www.omdbapi.com/?s={requests.utils.quote(keyword)}&apikey={api_key}"
    if year:
        url += f"&y={year}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("Response") == "False":
            return f"❌ Tidak ada film dengan kata kunci '{keyword}'."

        results = data.get("Search", [])[:5]  # Batasi 5 hasil
        output = f"🔍 Hasil pencarian untuk '{keyword}':\n"
        for i, movie in enumerate(results, 1):
            output += f"{i}. {movie['Title']} ({movie['Year']}) - {movie['Type'].title()}\n"
        return output
    except requests.RequestException as e:
        return f"❌ Gagal mencari film: {str(e)}"


imdb_agent = create_react_agent(
    model=llm,
    tools=[search_movie, search_movies_by_keyword],
    prompt=(
        "Kamu adalah IMDB agent. Tugasmu HANYA mencari informasi film dan serial TV.\n"
        "- Gunakan search_movie untuk detail lengkap satu film berdasarkan judul.\n"
        "- Gunakan search_movies_by_keyword untuk mencari daftar film berdasarkan kata kunci.\n"
        "- Sampaikan hasil dengan format yang rapi dan informatif dalam Bahasa Indonesia.\n"
        "- Jangan melakukan tugas selain informasi film/serial.\n"
        "- Setelah selesai, kembalikan hasilnya ke supervisor."
    ),
    name="imdb_agent",
)
