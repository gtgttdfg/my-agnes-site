import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "site.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Пользователи
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            credits INTEGER NOT NULL DEFAULT 5,
            created_at TEXT NOT NULL
        )
    """)

    # История генераций
    cur.execute("""
        CREATE TABLE IF NOT EXISTS generations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            prompt TEXT NOT NULL,
            model TEXT NOT NULL DEFAULT 'agnes-video-v2.0',
            status TEXT NOT NULL DEFAULT 'pending',
            video_path TEXT,
            error TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# ---------- Пользователи ----------

def create_user(username: str, password_hash: str, credits: int = 5):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password_hash, credits, created_at) VALUES (?, ?, ?, ?)",
            (username, password_hash, credits, datetime.utcnow().isoformat())
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user_by_username(username: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_credits(user_id: int) -> int:
    user = get_user_by_id(user_id)
    return user["credits"] if user else 0


def add_credits(user_id: int, amount: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET credits = credits + ? WHERE id = ?", (amount, user_id))
    conn.commit()
    conn.close()


def spend_credit(user_id: int) -> bool:
    """Списывает 1 кредит. Возвращает True, если удалось."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT credits FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    if not row or row["credits"] < 1:
        conn.close()
        return False
    cur.execute("UPDATE users SET credits = credits - 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return True


# ---------- Генерации ----------

def create_generation(user_id: int, prompt: str, model: str = "agnes-video-v2.0"):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO generations (user_id, prompt, model, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
        (user_id, prompt, model, datetime.utcnow().isoformat())
    )
    conn.commit()
    gen_id = cur.lastrowid
    conn.close()
    return gen_id


def update_generation(gen_id: int, status: str, video_path: str = None, error: str = None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE generations SET status = ?, video_path = ?, error = ? WHERE id = ?",
        (status, video_path, error, gen_id)
    )
    conn.commit()
    conn.close()


def get_user_generations(user_id: int, limit: int = 20):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM generations WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_generation(gen_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM generations WHERE id = ?", (gen_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


# ---------- Инициализация при импорте ----------

if __name__ == "__main__":
    init_db()
    print("✅ База данных создана:", DB_PATH)