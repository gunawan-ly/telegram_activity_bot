import sqlite3
from datetime import datetime, date, timezone, timedelta
from config import DB_FILE

WITA = timezone(timedelta(hours=8))

def _get_conn():
    """Membuat koneksi ke database SQLite."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Menginisialisasi database dan membuat/migrasi tabel."""
    conn = _get_conn()
    cursor = conn.cursor()

    # --- Tabel tasks (dengan kolom baru) ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            task TEXT NOT NULL,
            time TEXT NOT NULL,
            date TEXT DEFAULT NULL,
            category TEXT DEFAULT 'umum',
            done INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # --- Migrasi: tambah kolom jika belum ada (untuk database lama) ---
    try:
        cursor.execute("SELECT date FROM tasks LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE tasks ADD COLUMN date TEXT DEFAULT NULL")

    try:
        cursor.execute("SELECT category FROM tasks LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE tasks ADD COLUMN category TEXT DEFAULT 'umum'")

    try:
        cursor.execute("SELECT done FROM tasks LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE tasks ADD COLUMN done INTEGER DEFAULT 0")

    # --- Tabel notes ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

# =============================================
#  FUNGSI TUGAS (TASKS)
# =============================================

def add_task(chat_id, task, time, date_str=None, category='umum'):
    """Menambahkan tugas baru ke database."""
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO tasks (chat_id, task, time, date, category) VALUES (?, ?, ?, ?, ?)',
        (chat_id, task, time, date_str, category)
    )
    conn.commit()
    conn.close()

def get_all_tasks(chat_id, category_filter=None):
    """Mengembalikan semua tugas untuk chat_id tertentu, opsional filter kategori."""
    conn = _get_conn()
    cursor = conn.cursor()
    if category_filter:
        cursor.execute(
            'SELECT id, task, time, date, category, done FROM tasks WHERE chat_id = ? AND category = ? ORDER BY done ASC, time ASC',
            (chat_id, category_filter)
        )
    else:
        cursor.execute(
            'SELECT id, task, time, date, category, done FROM tasks WHERE chat_id = ? ORDER BY done ASC, time ASC',
            (chat_id,)
        )
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_today_tasks(chat_id):
    """Mengembalikan tugas untuk hari ini (harian + tanggal hari ini dalam WITA)."""
    today_str = datetime.now(WITA).strftime("%d-%m-%Y")
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, task, time, date, category, done FROM tasks WHERE chat_id = ? AND (date IS NULL OR date = ?) ORDER BY done ASC, time ASC',
        (chat_id, today_str)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_tasks_by_time(time_str):
    """Mengembalikan tugas aktif yang sesuai dengan waktu tertentu (hanya yang belum selesai)."""
    today_str = datetime.now(WITA).strftime("%d-%m-%Y")
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT chat_id, task FROM tasks WHERE time = ? AND done = 0 AND (date IS NULL OR date = ?)',
        (time_str, today_str)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def toggle_task_done(task_id, chat_id):
    """Mengubah status tugas antara selesai/belum selesai. Mengembalikan status baru."""
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT done FROM tasks WHERE id = ? AND chat_id = ?', (task_id, chat_id))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        return None
    new_status = 0 if row['done'] else 1
    cursor.execute('UPDATE tasks SET done = ? WHERE id = ? AND chat_id = ?', (new_status, task_id, chat_id))
    conn.commit()
    conn.close()
    return new_status

def delete_task(task_id, chat_id):
    """Menghapus tugas berdasarkan ID-nya untuk chat_id tertentu."""
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE id = ? AND chat_id = ?', (task_id, chat_id))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def clear_all_tasks(chat_id):
    """Menghapus SEMUA tugas untuk chat_id tertentu."""
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE chat_id = ?', (chat_id,))
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count

def get_task_stats(chat_id):
    """Mengembalikan statistik tugas: total, selesai, belum selesai."""
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as total FROM tasks WHERE chat_id = ?', (chat_id,))
    total = cursor.fetchone()['total']
    cursor.execute('SELECT COUNT(*) as done FROM tasks WHERE chat_id = ? AND done = 1', (chat_id,))
    done = cursor.fetchone()['done']
    conn.close()
    return {'total': total, 'selesai': done, 'belum': total - done}

def get_categories(chat_id):
    """Mengembalikan daftar kategori unik milik pengguna."""
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT category FROM tasks WHERE chat_id = ? ORDER BY category', (chat_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row['category'] for row in rows]

# =============================================
#  FUNGSI CATATAN (NOTES)
# =============================================

def add_note(chat_id, content):
    """Menambahkan catatan baru."""
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO notes (chat_id, content) VALUES (?, ?)', (chat_id, content))
    conn.commit()
    conn.close()

def get_all_notes(chat_id):
    """Mengembalikan semua catatan untuk chat_id tertentu."""
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT id, content, created_at FROM notes WHERE chat_id = ? ORDER BY created_at DESC', (chat_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_note(note_id, chat_id):
    """Menghapus catatan berdasarkan ID-nya."""
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM notes WHERE id = ? AND chat_id = ?', (note_id, chat_id))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def clear_all_notes(chat_id):
    """Menghapus semua catatan untuk chat_id tertentu."""
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM notes WHERE chat_id = ?', (chat_id,))
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count
