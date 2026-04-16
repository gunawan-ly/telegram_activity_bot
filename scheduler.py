import logging
from datetime import datetime, timezone, timedelta
from database import get_tasks_by_time

# Konfigurasi logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Zona Waktu Indonesia Tengah (WITA = UTC+8)
WITA = timezone(timedelta(hours=8))

async def check_reminders(context):
    """
    Fungsi callback untuk memeriksa pengingat.
    Dijalankan secara berkala oleh JobQueue.
    Hanya mengirim pengingat untuk tugas yang:
    - Belum selesai (done = 0)
    - Cocok tanggalnya (harian ATAU tanggal hari ini)
    """
    try:
        # Gunakan waktu WITA
        current_time = datetime.now(WITA).strftime("%H:%M")
        tasks = get_tasks_by_time(current_time)

        if tasks:
            logger.info(f"Menemukan {len(tasks)} pengingat untuk pukul {current_time}")

        for chat_id, task_text in tasks:
            message = (
                f"🔔 *PENGINGAT*\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📌 *{task_text}*\n"
                f"⏰ Pukul {current_time}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"_Jangan lupa ya!_ 💪"
            )
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
                logger.info(f"Berhasil mengirim pengingat ke {chat_id}: {task_text}")
            except Exception as e:
                logger.error(f"Gagal mengirim pengingat ke {chat_id}: {e}")

    except Exception as e:
        logger.error(f"Kesalahan dalam pengecekan pengingat: {e}")
