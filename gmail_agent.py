"""
gmail_agent.py
Agent spesialis untuk mengelola Gmail dan Google Calendar via Google API.
Menggunakan OAuth2 untuk autentikasi yang aman.
"""

import os
import json
from datetime import datetime, timedelta
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

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
]


def get_google_service(service_name: str, version: str):
    """Membuat Google API service dengan autentikasi OAuth2."""
    try:
        import json
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = None
        token_path = os.getenv("GMAIL_TOKEN_PATH", "token.json")
        creds_path = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")

        # Coba load token dari env var (untuk Streamlit Cloud)
        token_json_str = os.getenv("GMAIL_TOKEN_JSON")
        if token_json_str:
            creds = Credentials.from_authorized_user_info(
                json.loads(token_json_str), SCOPES
            )
        elif os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Simpan token yang sudah di-refresh ke file (lokal)
                if not token_json_str:
                    with open(token_path, "w") as token:
                        token.write(creds.to_json())
            else:
                if not os.path.exists(creds_path):
                    raise FileNotFoundError(
                        f"File credentials.json tidak ditemukan di '{creds_path}'. "
                        "Download dari Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
                with open(token_path, "w") as token:
                    token.write(creds.to_json())

        return build(service_name, version, credentials=creds)
    except ImportError:
        raise ImportError(
            "Google API libraries tidak terinstall. "
            "Jalankan: pip install google-auth google-auth-oauthlib google-api-python-client"
        )


@tool
def send_gmail(to: str, subject: str, body: str) -> str:
    """
    Mengirim email melalui Gmail.
    Parameter:
    - to: alamat email penerima
    - subject: subjek email
    - body: isi email
    """
    try:
        import base64
        from email.mime.text import MIMEText

        service = get_google_service("gmail", "v1")
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return f"✅ Email berhasil dikirim ke {to} dengan subjek '{subject}'."
    except FileNotFoundError as e:
        return f"❌ {str(e)}"
    except Exception as e:
        return f"❌ Gagal mengirim email: {str(e)}"


@tool
def read_recent_emails(max_results: int = 5) -> str:
    """
    Membaca email terbaru dari Gmail inbox.
    Parameter max_results: jumlah email yang ingin dibaca (default 5).
    """
    try:
        service = get_google_service("gmail", "v1")
        results = service.users().messages().list(
            userId="me", maxResults=max_results, labelIds=["INBOX"]
        ).execute()
        messages = results.get("messages", [])

        if not messages:
            return "📭 Tidak ada email di inbox."

        output = f"📬 {len(messages)} email terbaru:\n"
        for i, msg in enumerate(messages, 1):
            detail = service.users().messages().get(
                userId="me", id=msg["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()
            headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
            output += (
                f"\n{i}. Dari: {headers.get('From', 'N/A')}\n"
                f"   Subjek: {headers.get('Subject', 'N/A')}\n"
                f"   Tanggal: {headers.get('Date', 'N/A')}\n"
            )
        return output
    except FileNotFoundError as e:
        return f"❌ {str(e)}"
    except Exception as e:
        return f"❌ Gagal membaca email: {str(e)}"


@tool
def create_calendar_event(
    title: str,
    start_datetime: str,
    end_datetime: str,
    description: str = "",
    attendees: str = ""
) -> str:
    """
    Membuat acara baru di Google Calendar.
    Parameter:
    - title: judul acara
    - start_datetime: waktu mulai format 'YYYY-MM-DDTHH:MM:SS' (contoh: '2024-12-25T10:00:00')
    - end_datetime: waktu selesai format 'YYYY-MM-DDTHH:MM:SS'
    - description: deskripsi acara (opsional)
    - attendees: email peserta dipisah koma (opsional)
    """
    try:
        service = get_google_service("calendar", "v3")
        event = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start_datetime, "timeZone": "Asia/Jakarta"},
            "end": {"dateTime": end_datetime, "timeZone": "Asia/Jakarta"},
        }
        if attendees:
            event["attendees"] = [
                {"email": e.strip()} for e in attendees.split(",") if e.strip()
            ]

        created = service.events().insert(calendarId="primary", body=event).execute()
        return (
            f"✅ Acara '{title}' berhasil dibuat!\n"
            f"- Waktu: {start_datetime} s/d {end_datetime}\n"
            f"- Link: {created.get('htmlLink', 'N/A')}"
        )
    except FileNotFoundError as e:
        return f"❌ {str(e)}"
    except Exception as e:
        return f"❌ Gagal membuat acara: {str(e)}"


@tool
def list_upcoming_events(max_results: int = 5) -> str:
    """
    Menampilkan acara mendatang dari Google Calendar.
    Parameter max_results: jumlah acara yang ditampilkan (default 5).
    """
    try:
        service = get_google_service("calendar", "v3")
        now = datetime.utcnow().isoformat() + "Z"
        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = events_result.get("items", [])

        if not events:
            return "📅 Tidak ada acara mendatang."

        output = f"📅 {len(events)} acara mendatang:\n"
        for i, event in enumerate(events, 1):
            start = event["start"].get("dateTime", event["start"].get("date"))
            output += f"\n{i}. {event.get('summary', 'Tanpa Judul')}\n   Waktu: {start}\n"
            if event.get("description"):
                output += f"   Deskripsi: {event['description']}\n"
        return output
    except FileNotFoundError as e:
        return f"❌ {str(e)}"
    except Exception as e:
        return f"❌ Gagal mengambil acara: {str(e)}"


gmail_agent = create_react_agent(
    model=llm,
    tools=[send_gmail, read_recent_emails, create_calendar_event, list_upcoming_events],
    prompt=(
        "Kamu adalah Gmail & Calendar agent. Tugasmu mengelola email dan kalender Google.\n"
        "Tools yang tersedia:\n"
        "- send_gmail: kirim email ke alamat tertentu\n"
        "- read_recent_emails: baca email terbaru di inbox\n"
        "- create_calendar_event: buat acara baru di Google Calendar\n"
        "- list_upcoming_events: lihat acara mendatang\n\n"
        "- Selalu konfirmasi detail sebelum mengirim email atau membuat acara.\n"
        "- Gunakan format datetime 'YYYY-MM-DDTHH:MM:SS' untuk acara kalender.\n"
        "- Sampaikan hasil dengan jelas dalam Bahasa Indonesia.\n"
        "- Setelah selesai, kembalikan hasilnya ke supervisor."
    ),
    name="gmail_agent",
)
