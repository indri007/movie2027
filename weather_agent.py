"""
weather_agent.py
Agent spesialis untuk mengambil informasi cuaca real-time via OpenWeatherMap API.
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
def fetch_weather(city: str) -> str:
    """
    Mengambil informasi cuaca terkini untuk kota tertentu.
    Mengembalikan suhu, kelembaban, kecepatan angin, dan deskripsi cuaca.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "❌ OPENWEATHER_API_KEY tidak ditemukan di environment."

    city = city.strip().strip('"').strip("'")
    url = (
        f"http://api.openweathermap.org/data/2.5/weather"
        f"?q={city}&appid={api_key}&units=metric&lang=id"
    )
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return (
            f"Cuaca di {city.title()}:\n"
            f"- Kondisi: {data['weather'][0]['description'].title()}\n"
            f"- Suhu: {data['main']['temp']}°C (terasa seperti {data['main']['feels_like']}°C)\n"
            f"- Kelembaban: {data['main']['humidity']}%\n"
            f"- Kecepatan Angin: {data['wind']['speed']} m/s\n"
            f"- Tekanan Udara: {data['main']['pressure']} hPa"
        )
    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            return f"❌ Kota '{city}' tidak ditemukan. Pastikan nama kota benar."
        return f"❌ HTTP error: {str(e)}"
    except requests.RequestException as e:
        return f"❌ Gagal mengambil data cuaca: {str(e)}"


weather_agent = create_react_agent(
    model=llm,
    tools=[fetch_weather],
    prompt=(
        "Kamu adalah weather agent. Tugasmu HANYA mengambil data cuaca menggunakan tool fetch_weather.\n"
        "- Selalu gunakan tool fetch_weather untuk mendapatkan data cuaca.\n"
        "- Sampaikan hasil dengan jelas dan ringkas dalam Bahasa Indonesia.\n"
        "- Jangan melakukan tugas selain cuaca.\n"
        "- Setelah selesai, kembalikan hasilnya ke supervisor."
    ),
    name="weather_agent",
)
