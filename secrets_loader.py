"""
secrets_loader.py
Inject st.secrets ke os.environ untuk Streamlit Cloud.
Di lokal, .env sudah dihandle oleh load_dotenv() di masing-masing modul.
"""

import os
import streamlit as st

SECRET_KEYS = [
    "OPENAI_API_KEY",
    "OPENWEATHER_API_KEY",
    "OMDB_API_KEY",
    "QDRANT_URL",
    "QDRANT_API_KEY",
    "QDRANT_COLLECTION",
    "GMAIL_CREDENTIALS_PATH",
    "GMAIL_TOKEN_PATH",
    "GMAIL_TOKEN_JSON",
]


def load_secrets():
    """Inject Streamlit secrets ke os.environ jika tersedia dan nilainya bukan placeholder."""
    try:
        for key in SECRET_KEYS:
            if key in st.secrets:
                value = str(st.secrets[key])
                # Jangan override jika sudah ada dari .env, dan skip placeholder
                if not os.environ.get(key) and not value.startswith("your_"):
                    os.environ[key] = value
    except Exception:
        # st.secrets tidak tersedia (lokal tanpa secrets.toml) — tidak masalah
        pass
