"""
Modul AI — Integrasi OpenRouter API
Menggunakan OpenAI Python SDK yang diarahkan ke endpoint OpenRouter.
Mendukung percakapan multi-turn dengan riwayat per pengguna.
"""

import logging
from openai import OpenAI
from config import OPENROUTER_API_KEY, AI_MODEL

logger = logging.getLogger(__name__)

# Inisialisasi klien OpenAI ke endpoint OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY or "sk-placeholder",
)

# Riwayat percakapan per chat_id (disimpan di memori)
# Format: { chat_id: [{"role": "...", "content": "..."}, ...] }
_conversations = {}

# System prompt untuk kepribadian bot
SYSTEM_PROMPT = (
    "Kamu adalah asisten pribadi yang cerdas, ramah, dan membantu. "
    "Namamu adalah 'Asisten Aktivitas'. "
    "Kamu membantu pengguna mengatur jadwal harian, memberikan motivasi, "
    "dan menjawab pertanyaan dengan bahasa Indonesia yang santai dan sopan. "
    "Jawab secara singkat dan padat kecuali diminta penjelasan detail. "
    "Gunakan emoji sesekali agar percakapan terasa hidup."
)

MAX_HISTORY = 20  # Maksimal jumlah pesan dalam riwayat per pengguna


def get_conversation(chat_id):
    """Mengambil riwayat percakapan untuk chat_id tertentu."""
    if chat_id not in _conversations:
        _conversations[chat_id] = []
    return _conversations[chat_id]


def clear_conversation(chat_id):
    """Menghapus riwayat percakapan untuk chat_id tertentu."""
    _conversations[chat_id] = []


async def chat_with_ai(chat_id, user_message):
    """
    Mengirim pesan ke AI melalui OpenRouter dan mengembalikan respons.
    Mendukung percakapan multi-turn dengan riwayat.
    """
    if not OPENROUTER_API_KEY:
        return "❌ API Key OpenRouter belum diatur. Silakan set OPENROUTER_API_KEY di file .env"

    history = get_conversation(chat_id)

    # Tambahkan pesan pengguna ke riwayat
    history.append({"role": "user", "content": user_message})

    # Potong riwayat jika terlalu panjang
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
        _conversations[chat_id] = history

    # Bangun daftar pesan dengan system prompt di awal
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    try:
        completion = client.chat.completions.create(
            extra_headers={
                "X-OpenRouter-Title": "Telegram Activity Bot",
            },
            model=AI_MODEL,
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
        )

        # Ambil respons dari AI
        ai_reply = completion.choices[0].message.content

        # Tambahkan respons AI ke riwayat
        history.append({"role": "assistant", "content": ai_reply})

        logger.info(f"AI reply to {chat_id}: {ai_reply[:80]}...")
        return ai_reply

    except Exception as e:
        logger.error(f"OpenRouter API Error: {e}")
        return f"❌ Gagal menghubungi AI: {str(e)}"
