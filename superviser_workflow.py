"""
superviser_workflow.py
Supervisor multi-agent workflow untuk Personal AI Assistant.
Mengkoordinasikan: weather_agent, imdb_agent, gmail_agent, dan RAG tool.
"""

import os
from typing import Annotated
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, convert_to_messages
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.types import Command, Send
from langgraph.prebuilt import create_react_agent, InjectedState
from langchain_core.tools import tool

from weather_agent import weather_agent
from imdb_agent import imdb_agent
from gmail_agent import gmail_agent
from rag_tool import rag_search

load_dotenv()

# === LLM Supervisor ===
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.1,
    max_tokens=1000,
)

SUPERVISOR_PROMPT = """Kamu adalah supervisor AI asisten pribadi yang cerdas dan membantu.
Kamu mengelola tiga agent spesialis dan satu RAG tool:

AGENT SPESIALIS:
- weather_agent: Menangani semua pertanyaan tentang cuaca (suhu, kondisi, prakiraan)
- imdb_agent: Menangani pencarian informasi film dan serial TV (rating, sutradara, sinopsis)
- gmail_agent: Menangani email (kirim/baca) dan Google Calendar (buat/lihat acara)

RAG TOOL:
- rag_search: Mencari informasi dari knowledge base tentang fitur asisten dan informasi umum

ATURAN DELEGASI:
1. Analisis permintaan pengguna dan tentukan agent yang tepat.
2. Untuk pertanyaan cuaca → delegasikan ke weather_agent.
3. Untuk pertanyaan film/serial → delegasikan ke imdb_agent.
4. Untuk email atau kalender → delegasikan ke gmail_agent.
5. Untuk pertanyaan tentang fitur asisten atau informasi umum → gunakan rag_search langsung.
6. Untuk tugas gabungan (misal: cek cuaca lalu kirim email) → jalankan secara berurutan.
7. Jangan kerjakan sendiri tugas yang bisa didelegasikan ke agent spesialis.
8. Setelah semua tugas selesai, rangkum hasilnya dengan ramah dalam Bahasa Indonesia.

Selalu berkomunikasi dalam Bahasa Indonesia kecuali diminta sebaliknya.
"""


def create_handoff_tool(agent_name: str, description: str):
    """Membuat tool untuk mendelegasikan tugas ke agent tertentu."""

    @tool(f"transfer_to_{agent_name}", description=description)
    def handoff_tool(
        task_description: Annotated[
            str,
            "Deskripsi tugas lengkap yang harus dikerjakan agent, termasuk semua konteks yang relevan.",
        ],
        state: Annotated[MessagesState, InjectedState],
    ) -> Command:
        task_message = {"role": "user", "content": task_description}
        agent_input = {**state, "messages": [task_message]}
        return Command(goto=[Send(agent_name, agent_input)], graph=Command.PARENT)

    return handoff_tool


# === Handoff Tools ===
transfer_to_weather = create_handoff_tool(
    "weather_agent",
    "Delegasikan tugas terkait cuaca ke weather agent. Sertakan nama kota yang ingin dicek."
)
transfer_to_imdb = create_handoff_tool(
    "imdb_agent",
    "Delegasikan tugas pencarian film/serial TV ke IMDB agent. Sertakan judul atau kata kunci."
)
transfer_to_gmail = create_handoff_tool(
    "gmail_agent",
    "Delegasikan tugas email atau kalender ke Gmail agent. Sertakan detail lengkap (penerima, subjek, isi, atau detail acara)."
)

# === Supervisor Agent ===
supervisor = create_react_agent(
    model=llm,
    tools=[transfer_to_weather, transfer_to_imdb, transfer_to_gmail, rag_search],
    prompt=SUPERVISOR_PROMPT,
    name="supervisor",
)

# === Build Workflow Graph ===
workflow = (
    StateGraph(MessagesState)
    .add_node(supervisor, destinations=("weather_agent", "imdb_agent", "gmail_agent"))
    .add_node(weather_agent)
    .add_node(imdb_agent)
    .add_node(gmail_agent)
    .add_edge(START, "supervisor")
    .add_edge("weather_agent", "supervisor")
    .add_edge("imdb_agent", "supervisor")
    .add_edge("gmail_agent", "supervisor")
    .compile()
)


def run_workflow(user_message: str, chat_history: list = None) -> str:
    """
    Menjalankan workflow supervisor dengan pesan pengguna dan riwayat chat.
    
    Args:
        user_message: Pesan terbaru dari pengguna
        chat_history: Daftar pesan sebelumnya [{"role": "user/assistant", "content": "..."}]
    
    Returns:
        Respons terakhir dari supervisor sebagai string
    """
    messages = []

    # Tambahkan chat history (maksimal 6 pesan terakhir = 3 percakapan)
    if chat_history:
        for msg in chat_history[-6:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

    # Tambahkan pesan terbaru
    messages.append(HumanMessage(content=user_message))

    result = workflow.invoke({"messages": messages})

    # Ambil respons terakhir dari supervisor (AIMessage tanpa tool_calls)
    final_messages = result.get("messages", [])
    for msg in reversed(final_messages):
        if (
            isinstance(msg, AIMessage)
            and msg.content
            and not getattr(msg, "tool_calls", None)
        ):
            return msg.content

    return "Maaf, saya tidak dapat memproses permintaan Anda saat ini."


if __name__ == "__main__":
    # Test sederhana
    print("=== Test Supervisor Workflow ===\n")
    response = run_workflow("Bagaimana cuaca di Jakarta hari ini?")
    print(f"Response: {response}")
