import os
from dotenv import load_dotenv

# Muat environment variables dari file .env
load_dotenv()

# Konfigurasi Bot Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN")
PROXY_URL = os.getenv("PROXY_URL")

# Konfigurasi OpenRouter AI
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "google/gemini-2.0-flash-001")

# Konfigurasi Database
DB_FILE = "schedule.db"

# Validasi
if not BOT_TOKEN:
    print("PERINGATAN: BOT_TOKEN tidak ditemukan. Bot tidak akan berjalan.")
if not OPENROUTER_API_KEY:
    print("PERINGATAN: OPENROUTER_API_KEY tidak ditemukan. Fitur AI tidak akan berfungsi.")
