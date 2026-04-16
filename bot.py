"""
Bot Manajer Aktivitas Pribadi Telegram
Versi: 4.0 (AI-Powered Edition)
Fitur: Tugas + Catatan + Statistik + AI Chat via OpenRouter
Library: python-telegram-bot v20+ | OpenAI SDK → OpenRouter
"""

import logging
import re
from datetime import datetime, timezone, timedelta

# Zona Waktu Indonesia Tengah (WITA = UTC+8)
WITA = timezone(timedelta(hours=8))

from telegram import (
    Update, ReplyKeyboardMarkup, 
    InlineKeyboardButton, InlineKeyboardMarkup, 
    BotCommand
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)

from config import BOT_TOKEN
from database import (
    init_db, add_task, get_all_tasks, get_today_tasks,
    delete_task, toggle_task_done, clear_all_tasks,
    get_task_stats, get_categories,
    add_note, get_all_notes, delete_note, clear_all_notes
)
from scheduler import check_reminders
from ai import chat_with_ai, clear_conversation

# Konfigurasi logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =============================================
#  EMOJI & KONSTANTA
# =============================================
CATEGORY_EMOJI = {
    'umum': '📌',
    'belajar': '📖',
    'kerja': '💼',
    'pribadi': '🏠',
    'olahraga': '🏃',
    'ibadah': '🕌',
    'hiburan': '🎮',
}

def cat_emoji(category):
    return CATEGORY_EMOJI.get(category, '📌')

# =============================================
#  KEYBOARD HELPERS
# =============================================
def get_main_menu_keyboard():
    keyboard = [
        ["📋 Daftar Tugas", "📅 Hari Ini"],
        ["📝 Catatan Saya", "📊 Statistik"],
        ["🤖 Chat AI", "📚 Rutinitas Sekolah"],
        ["❓ Bantuan"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def format_task_line(task_row):
    """Memformat satu tugas menjadi satu baris teks."""
    name = task_row['task']
    time = task_row['time']
    date_str = task_row['date']
    category = task_row['category'] or 'umum'
    done = task_row['done']

    status = "✅" if done else "⏳"
    name_display = f"~{name}~" if done else f"*{name}*"
    emoji = cat_emoji(category)
    
    line = f"{status} {name_display} — ⏰ {time}"
    if date_str:
        line += f" 📅 {date_str}"
    line += f" {emoji}"
    return line

def build_task_list_buttons(tasks):
    """Membuat tombol inline untuk setiap tugas dalam daftar."""
    buttons = []
    for task_row in tasks:
        tid = task_row['id']
        is_done = task_row['done']
        done_label = "↩️" if is_done else "✅"
        name_short = task_row['task'][:15]
        buttons.append([
            InlineKeyboardButton(f"{done_label} {name_short}", callback_data=f"done_{tid}"),
            InlineKeyboardButton("🗑️", callback_data=f"del_{tid}"),
        ])
    return InlineKeyboardMarkup(buttons)

# =============================================
#  HANDLERS — PERINTAH UTAMA
# =============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 *Halo! Selamat datang di Bot Manajer Aktivitas v4!*\n\n"
        "Saya adalah asisten pribadi Anda yang didukung *AI* untuk:\n"
        "• 📋 Mengatur tugas & jadwal harian\n"
        "• 📝 Menyimpan catatan cepat\n"
        "• ⏰ Mengirim pengingat otomatis\n"
        "• 📊 Memantau produktivitas\n"
        "• 🤖 Ngobrol dengan AI\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📌 *Cara Cepat Mulai:*\n"
        "• Tambah tugas: `/task Belajar 19:00`\n"
        "• Tanya AI: `/ai Apa tips belajar efektif?`\n"
        "• Gunakan tombol di bawah ↓"
    )
    await update.message.reply_text(
        welcome_text, parse_mode='Markdown',
        reply_markup=get_main_menu_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📜 *PANDUAN LENGKAP*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "➕ *Tambah Tugas*\n"
        "`/task <nama> <JJ:MM>`\n"
        "_Tugas harian, contoh:_ `/task Belajar 19:30`\n\n"
        "`/task <nama> <JJ:MM> <DD-MM-YYYY>`\n"
        "_Tugas tanggal tertentu:_ `/task Ujian 09:00 25-04-2026`\n\n"
        "`/task <nama> <JJ:MM> #kategori`\n"
        "_Dengan kategori:_ `/task Lari 06:00 #olahraga`\n\n"
        "📋 *Lihat Tugas*\n"
        "`/list` — Semua tugas\n"
        "`/today` — Tugas hari ini\n"
        "`/list #kategori` — Filter kategori\n\n"
        "📝 *Catatan*\n"
        "`/note <isi>` — Simpan catatan\n\n"
        "📊 *Statistik*\n"
        "`/stats` — Ringkasan tugas\n\n"
        "🤖 *AI Chat*\n"
        "`/ai <pertanyaan>` — Tanya AI apa saja\n"
        "`/reset` — Reset riwayat chat AI\n\n"
        "🗑️ *Hapus*\n"
        "`/clearall` — Hapus semua tugas\n\n"
        "🏷️ *Kategori Tersedia:*\n"
        "umum, belajar, kerja, pribadi, olahraga, ibadah, hiburan"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

# =============================================
#  HANDLERS — TUGAS
# =============================================

async def add_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ *Format Salah!*\n\n"
            "Contoh:\n"
            "• `/task Belajar 19:00`\n"
            "• `/task Ujian 09:00 25-04-2026`\n"
            "• `/task Lari 06:00 #olahraga`",
            parse_mode='Markdown'
        )
        return

    args = list(context.args)
    
    # Cari dan ekstrak kategori (#hashtag)
    category = 'umum'
    for i, arg in enumerate(args):
        if arg.startswith('#'):
            category = arg[1:].lower()
            if category not in CATEGORY_EMOJI:
                category = 'umum'
            args.pop(i)
            break
    
    # Cari dan ekstrak tanggal (DD-MM-YYYY)
    date_str = None
    for i, arg in enumerate(args):
        if re.match(r'^\d{2}-\d{2}-\d{4}$', arg):
            try:
                datetime.strptime(arg, "%d-%m-%Y")
                date_str = arg
                args.pop(i)
                break
            except ValueError:
                await update.message.reply_text("❌ *Tanggal Tidak Valid!*\n\nGunakan format DD-MM-YYYY.", parse_mode='Markdown')
                return

    # Argumen terakhir harus waktu
    if len(args) < 2:
        await update.message.reply_text("❌ *Format Salah!*\n\nPastikan ada nama tugas dan waktu.", parse_mode='Markdown')
        return
    
    time_str = args[-1]
    task_name = " ".join(args[:-1])

    if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', time_str):
        await update.message.reply_text("❌ *Waktu Salah!*\n\nGunakan format 24 jam (JJ:MM).", parse_mode='Markdown')
        return

    try:
        add_task(update.effective_chat.id, task_name, time_str, date_str, category)
        emoji = cat_emoji(category)
        
        response = (
            f"✅ *Tugas Tersimpan!*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📌 *{task_name}*\n"
            f"⏰ Pukul {time_str}\n"
        )
        if date_str:
            response += f"📅 Tanggal {date_str}\n"
        else:
            response += f"🔄 Tugas Harian\n"
        response += f"{emoji} Kategori: #{category}"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"DB Error: {e}")
        await update.message.reply_text("❌ Gagal menyimpan karena gangguan teknis.")

async def list_tasks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan semua tugas dalam satu pesan."""
    chat_id = update.effective_chat.id
    
    # Cek apakah ada filter kategori
    category_filter = None
    if context.args:
        for arg in context.args:
            if arg.startswith('#'):
                category_filter = arg[1:].lower()
    
    tasks = get_all_tasks(chat_id, category_filter)
    
    if not tasks:
        msg = "📭 *Tidak Ada Tugas*\n\n"
        if category_filter:
            msg += f"Tidak ada tugas dengan kategori #{category_filter}."
        else:
            msg += "Anda belum memiliki tugas. Tambahkan dengan `/task`."
        await update.message.reply_text(msg, parse_mode='Markdown')
        return

    title = f"📋 *Daftar Tugas"
    if category_filter:
        title += f" (#{category_filter})"
    title += f"* — {len(tasks)} item\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    lines = [title]
    for task_row in tasks:
        lines.append(format_task_line(task_row))
    
    text = "\n".join(lines)
    buttons = build_task_list_buttons(tasks)
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=buttons)

async def today_tasks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan tugas untuk hari ini dalam satu pesan."""
    chat_id = update.effective_chat.id
    tasks = get_today_tasks(chat_id)
    
    today_display = datetime.now(WITA).strftime("%A, %d %B %Y")
    
    if not tasks:
        await update.message.reply_text(
            f"📅 *Jadwal Hari Ini*\n_{today_display}_\n\n📭 Tidak ada tugas untuk hari ini.",
            parse_mode='Markdown'
        )
        return

    done_count = sum(1 for t in tasks if t['done'])
    header = (
        f"📅 *Jadwal Hari Ini*\n"
        f"_{today_display}_\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 {done_count}/{len(tasks)} selesai\n\n"
    )
    
    lines = [header]
    for task_row in tasks:
        lines.append(format_task_line(task_row))
    
    text = "\n".join(lines)
    buttons = build_task_list_buttons(tasks)
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=buttons)

# =============================================
#  HANDLERS — CATATAN
# =============================================

async def note_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ *Format Salah!*\n\nContoh: `/note Beli buku matematika`",
            parse_mode='Markdown'
        )
        return

    content = " ".join(context.args)
    try:
        add_note(update.effective_chat.id, content)
        await update.message.reply_text(
            f"📝 *Catatan Tersimpan!*\n━━━━━━━━━━━━━━━\n💬 _{content}_",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Note Error: {e}")
        await update.message.reply_text("❌ Gagal menyimpan catatan.")

async def list_notes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    notes = get_all_notes(update.effective_chat.id)
    
    if not notes:
        await update.message.reply_text(
            "📝 *Catatan Saya*\n\n📭 Belum ada catatan. Tambahkan dengan `/note`.",
            parse_mode='Markdown'
        )
        return

    lines = [f"📝 *Catatan Saya* — {len(notes)} item\n━━━━━━━━━━━━━━━━━━━━\n"]
    buttons = []
    for note in notes:
        created = note['created_at'][:16] if note['created_at'] else ""
        lines.append(f"💬 _{note['content']}_  🕐 {created}")
        name_short = note['content'][:18]
        buttons.append([InlineKeyboardButton(f"🗑️ {name_short}", callback_data=f"delnote_{note['id']}")])
    
    text = "\n".join(lines)
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)

# =============================================
#  HANDLERS — STATISTIK
# =============================================

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    stats = get_task_stats(chat_id)
    categories = get_categories(chat_id)
    notes = get_all_notes(chat_id)
    
    if stats['total'] == 0 and len(notes) == 0:
        await update.message.reply_text(
            "📊 *Statistik*\n\n📭 Belum ada data. Mulai tambahkan tugas atau catatan!",
            parse_mode='Markdown'
        )
        return

    # Progress bar
    if stats['total'] > 0:
        pct = int((stats['selesai'] / stats['total']) * 100)
        filled = int(pct / 10)
        bar = "█" * filled + "░" * (10 - filled)
    else:
        pct = 0
        bar = "░" * 10

    # Penentuan emoji motivasi
    if pct == 100:
        motivasi = "🏆 Sempurna! Semua tugas selesai!"
    elif pct >= 75:
        motivasi = "🔥 Luar biasa! Hampir selesai semua!"
    elif pct >= 50:
        motivasi = "💪 Bagus! Lebih dari setengah selesai!"
    elif pct >= 25:
        motivasi = "🌱 Ayo semangat! Masih banyak yang bisa dicapai!"
    else:
        motivasi = "🚀 Yuk mulai selesaikan tugas Anda!"

    cat_text = ""
    if categories:
        cat_list = [f"{cat_emoji(c)} #{c}" for c in categories]
        cat_text = f"\n🏷️ *Kategori:* {', '.join(cat_list)}"
    
    response = (
        f"📊 *STATISTIK ANDA*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 *Tugas*\n"
        f"   Total: {stats['total']}\n"
        f"   ✅ Selesai: {stats['selesai']}\n"
        f"   ⏳ Belum: {stats['belum']}\n\n"
        f"   [{bar}] {pct}%\n\n"
        f"📝 *Catatan:* {len(notes)} item"
        f"{cat_text}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{motivasi}"
    )
    await update.message.reply_text(response, parse_mode='Markdown')

# =============================================
#  HANDLERS — UTILITAS
# =============================================

async def clear_all_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menghapus semua tugas dengan konfirmasi."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Ya, Hapus Semua", callback_data="confirm_clearall"),
            InlineKeyboardButton("❌ Batal", callback_data="cancel_clearall"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "⚠️ *Konfirmasi Hapus Semua*\n\n"
        "Apakah Anda yakin ingin menghapus SEMUA tugas?\n"
        "_Tindakan ini tidak dapat dibatalkan._",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def routine_school(update: Update, context: ContextTypes.DEFAULT_TYPE):
    preset = [
        ("Bangun tidur", "07:00", "pribadi"),
        ("Istirahat", "16:00", "pribadi"),
        ("Belajar", "19:00", "belajar"),
        ("PR Sekolah", "21:00", "belajar"),
        ("Tidur", "22:00", "pribadi"),
    ]
    chat_id = update.effective_chat.id
    try:
        for task, time, cat in preset:
            add_task(chat_id, task, time, category=cat)
        
        items = "\n".join([f"   {cat_emoji(c)} {t} — {tm}" for t, tm, c in preset])
        await update.message.reply_text(
            f"📚 *Rutinitas Sekolah Dimuat!*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n{items}\n\n"
            f"_Semua tugas di atas kini terdaftar sebagai tugas harian._",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Routine error: {e}")
        await update.message.reply_text("❌ Gagal memuat jadwal.")

# =============================================
#  CALLBACK HANDLER (Tombol Inline)
# =============================================

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("done_"):
        task_id = int(data.split("_")[1])
        new_status = toggle_task_done(task_id, query.from_user.id)
        if new_status is not None:
            label = "✅ Ditandai selesai!" if new_status else "↩️ Dikembalikan ke belum selesai."
            await query.edit_message_text(text=label)
        else:
            await query.edit_message_text(text="❌ Tugas tidak ditemukan.")

    elif data.startswith("del_"):
        task_id = int(data.split("_")[1])
        success = delete_task(task_id, query.from_user.id)
        if success:
            await query.edit_message_text(text="🗑️ Tugas telah dihapus.")
        else:
            await query.edit_message_text(text="❌ Gagal menghapus tugas.")

    elif data.startswith("delnote_"):
        note_id = int(data.split("_")[1])
        success = delete_note(note_id, query.from_user.id)
        if success:
            await query.edit_message_text(text="🗑️ Catatan telah dihapus.")
        else:
            await query.edit_message_text(text="❌ Gagal menghapus catatan.")

    elif data == "confirm_clearall":
        count = clear_all_tasks(query.from_user.id)
        await query.edit_message_text(text=f"🗑️ {count} tugas telah dihapus semua.")

    elif data == "cancel_clearall":
        await query.edit_message_text(text="👍 Penghapusan dibatalkan.")

# =============================================
#  HANDLERS — AI CHAT
# =============================================

async def ai_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani perintah /ai untuk chat dengan AI."""
    if not context.args:
        await update.message.reply_text(
            "🤖 *Chat AI*\n\n"
            "Tanya apa saja! Contoh:\n"
            "• `/ai Apa tips belajar efektif?`\n"
            "• `/ai Buatkan jadwal belajar untuk ujian`\n"
            "• `/ai Motivasi untuk hari ini`",
            parse_mode='Markdown'
        )
        return

    user_message = " ".join(context.args)
    chat_id = update.effective_chat.id

    # Kirim indikator "sedang mengetik"
    await update.effective_chat.send_action(action="typing")

    reply = await chat_with_ai(chat_id, user_message)
    await update.message.reply_text(reply)

async def reset_ai_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menghapus riwayat percakapan AI."""
    clear_conversation(update.effective_chat.id)
    await update.message.reply_text("🔄 Riwayat percakapan AI telah direset.")

# =============================================
#  HANDLER — TOMBOL MENU TEKS & AI FALLBACK
# =============================================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📋 Daftar Tugas":
        await list_tasks_handler(update, context)
    elif text == "📅 Hari Ini":
        await today_tasks_handler(update, context)
    elif text == "📝 Catatan Saya":
        await list_notes_handler(update, context)
    elif text == "📊 Statistik":
        await stats_handler(update, context)
    elif text == "🤖 Chat AI":
        await update.message.reply_text(
            "🤖 *Mode Chat AI Aktif!*\n\n"
            "Ketik pesan Anda langsung atau gunakan `/ai <pertanyaan>`\n\n"
            "_Ketik /reset untuk menghapus riwayat percakapan._",
            parse_mode='Markdown'
        )
    elif text == "📚 Rutinitas Sekolah":
        await routine_school(update, context)
    elif text == "❓ Bantuan":
        await help_command(update, context)
    else:
        # Pesan teks biasa yang tidak cocok menu → kirim ke AI
        chat_id = update.effective_chat.id
        await update.effective_chat.send_action(action="typing")
        reply = await chat_with_ai(chat_id, text)
        await update.message.reply_text(reply)

# =============================================
#  INISIALISASI & MAIN
# =============================================

async def post_init(application):
    """Pengaturan awal setelah bot aktif."""
    commands = [
        BotCommand("start", "Memulai bot"),
        BotCommand("help", "Panduan lengkap"),
        BotCommand("task", "Tambah tugas"),
        BotCommand("list", "Daftar semua tugas"),
        BotCommand("today", "Tugas hari ini"),
        BotCommand("note", "Simpan catatan"),
        BotCommand("stats", "Lihat statistik"),
        BotCommand("ai", "Tanya AI"),
        BotCommand("reset", "Reset chat AI"),
        BotCommand("routine_school", "Jadwal sekolah"),
        BotCommand("clearall", "Hapus semua tugas"),
    ]
    await application.bot.set_my_commands(commands)
    application.job_queue.run_repeating(check_reminders, interval=60, first=10)
    logger.info("Bot v4.0 (AI-Powered) siap! JobQueue pengingat telah dijadwalkan.")

if __name__ == '__main__':
    init_db()
    if not BOT_TOKEN:
        print("BOT_TOKEN is missing!")
        exit(1)

    # Build application dengan timeout yang lebih besar
    builder = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
    )

    # Tambahkan proxy jika diset di .env
    from config import PROXY_URL
    if PROXY_URL:
        from telegram.request import HTTPXRequest
        request = HTTPXRequest(
            connection_pool_size=8,
            connect_timeout=30,
            read_timeout=30,
            write_timeout=30,
            pool_timeout=30,
            proxy=PROXY_URL,
        )
        builder = builder.request(request)
        print(f"Menggunakan proxy: {PROXY_URL}")

    application = builder.build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("task", add_task_handler))
    application.add_handler(CommandHandler("list", list_tasks_handler))
    application.add_handler(CommandHandler("today", today_tasks_handler))
    application.add_handler(CommandHandler("note", note_handler))
    application.add_handler(CommandHandler("stats", stats_handler))
    application.add_handler(CommandHandler("ai", ai_chat_handler))
    application.add_handler(CommandHandler("reset", reset_ai_handler))
    application.add_handler(CommandHandler("routine_school", routine_school))
    application.add_handler(CommandHandler("clearall", clear_all_handler))

    # Text menu & inline button handlers (termasuk AI fallback)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    print("Bot v4.0 (AI-Powered) sedang berjalan...")
    print("Tekan Ctrl+C untuk menghentikan.\n")
    application.run_polling(drop_pending_updates=True)

