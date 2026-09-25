"""
app.py
Streamlit UI untuk Personal AI Assistant dengan multi-agent supervisor.
Fitur: cuaca, film/IMDB, Gmail, Google Calendar, dan RAG knowledge base.
Kompatibel untuk lokal (.env) dan Streamlit Cloud (st.secrets).
"""

import streamlit as st
import os
import uuid
from secrets_loader import load_secrets

# Inject secrets ke os.environ (untuk Streamlit Cloud)
load_secrets()

from superviser_workflow import run_workflow
from chat_history import save_message, load_history, clear_history, list_sessions

# === Konfigurasi Halaman ===
st.set_page_config(
    page_title="Personal AI Assistant",
    page_icon="🤖",
    layout="centered",
)

# === CSS Kustom ===
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        border-bottom: 2px solid #f0f2f6;
        margin-bottom: 1.5rem;
    }
    .capability-card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        margin: 0.3rem 0;
        border-left: 3px solid #4CAF50;
        font-size: 0.9rem;
    }
    .chat-info {
        font-size: 0.8rem;
        color: #888;
        text-align: center;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# === Header ===
st.markdown("""
<div class="main-header">
    <h1>🤖 Personal AI Assistant</h1>
    <p>Asisten pribadi cerdas dengan kemampuan cuaca, film, email & kalender</p>
</div>
""", unsafe_allow_html=True)

# === Inisialisasi Session State ===
# session_id dibuat sekali per browser session, history diload dari Qdrant
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())
    st.session_state["messages"] = []  # chat baru by default

if "messages" not in st.session_state:
    st.session_state["messages"] = []

# === Sidebar ===
with st.sidebar:
    st.header("🛠️ Kemampuan Asisten")

    st.markdown("**🎬 Film & Serial**")
    st.markdown('<div class="capability-card">Cari info film, rating IMDb, sinopsis</div>', unsafe_allow_html=True)

    st.markdown("**🌤️ Cuaca**")
    st.markdown('<div class="capability-card">Cek cuaca real-time di kota manapun</div>', unsafe_allow_html=True)

    st.markdown("**📧 Gmail**")
    st.markdown('<div class="capability-card">Kirim & baca email via Gmail</div>', unsafe_allow_html=True)

    st.markdown("**📅 Kalender**")
    st.markdown('<div class="capability-card">Buat & lihat acara Google Calendar</div>', unsafe_allow_html=True)

    st.markdown("**📚 Knowledge Base**")
    st.markdown('<div class="capability-card">Jawab pertanyaan dari knowledge base</div>', unsafe_allow_html=True)

    st.divider()

    if st.button("✏️ Chat Baru", use_container_width=True, type="primary"):
        st.session_state["session_id"] = str(uuid.uuid4())
        st.session_state["messages"] = []
        st.session_state.pop("example_input", None)
        st.rerun()

    if st.button("🗑️ Hapus Chat Ini", use_container_width=True):
        clear_history(st.session_state["session_id"])
        st.session_state["messages"] = []
        st.session_state.pop("example_input", None)
        st.rerun()

    st.markdown(
        '<div class="chat-info">Riwayat chat: 3 percakapan terakhir</div>',
        unsafe_allow_html=True
    )

    # === Daftar Session Lama ===
    st.divider()
    st.subheader("🕘 Riwayat Percakapan")
    sessions = list_sessions()
    if sessions:
        for s in sessions:
            sid = s["session_id"]
            preview = s["preview"] or "Percakapan tanpa judul"
            is_active = sid == st.session_state["session_id"]
            label = f"{'▶ ' if is_active else ''}{preview}"
            if st.button(label, key=f"sess_{sid}", use_container_width=True):
                st.session_state["session_id"] = sid
                st.session_state["messages"] = load_history(sid)
                st.rerun()
    else:
        st.caption("Belum ada riwayat percakapan.")

# === Tampilkan Riwayat Chat ===
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# === Input Chat ===
default_input = st.session_state.pop("example_input", "")
user_input = st.chat_input("Ketik pertanyaan atau perintah Anda...")

if default_input and not user_input:
    user_input = default_input

# === Proses Input ===
if user_input:
    # Tampilkan & simpan pesan user
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state["messages"].append({"role": "user", "content": user_input})
    save_message(st.session_state["session_id"], "user", user_input)

    # Proses & tampilkan respons assistant
    with st.chat_message("assistant"):
        with st.spinner("Memproses..."):
            try:
                history = st.session_state["messages"][:-1]
                response = run_workflow(user_input, chat_history=history)
            except Exception as e:
                response = f"❌ Terjadi kesalahan: {str(e)}\n\nPastikan semua API key sudah dikonfigurasi dengan benar di file `.env`."
        st.markdown(response)

    # Simpan respons ke history
    st.session_state["messages"].append({"role": "assistant", "content": response})
    save_message(st.session_state["session_id"], "assistant", response)
