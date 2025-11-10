import os, sqlite3, json, time, random, string
from typing import Dict, List
from ..core.config import CHATS_DIR

DB_PATH = os.path.join(CHATS_DIR, "sessions.sqlite")

def ensure_db():
    os.makedirs(CHATS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS chats (
        chat_id TEXT PRIMARY KEY,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
       
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS messages (
        chat_id TEXT,
        role TEXT,
        text TEXT,
        ts REAL
    )""")
    conn.commit()
    conn.close()

def _rand_suffix(n=8):
    return "".join(random.choices(string.hexdigits.lower(), k=n))

def new_chat_id(seq: int) -> str:
    return f"{seq:05d}-{_rand_suffix(8)}"

def next_seq() -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS seq (n INTEGER)")
    conn.commit()
    cur.execute("SELECT n FROM seq")
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO seq (n) VALUES (1)")
        conn.commit()
        n = 1
    else:
        n = row[0] + 1
        cur.execute("UPDATE seq SET n=?", (n,))
        conn.commit()
    conn.close()
    return n

def create_chat() -> str:
    ensure_db()
    cid = new_chat_id(next_seq())
    now = time.time()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO chats (chat_id, created_at, updated_at) VALUES (?,?,?)",
                (cid, now, now))
    conn.commit()
    conn.close()
    return cid

def get_chat(chat_id: str):
    ensure_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT chat_id, created_at, updated_at FROM chats WHERE chat_id=?", (chat_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "chat_id": row[0],
        # "kb_bindings": json.loads(row[1]),
        "created_at": row[1],
        "updated_at": row[2],
    }

def append_message(chat_id: str, role: str, text: str):
    ensure_db()
    now = time.time()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO messages (chat_id, role, text, ts) VALUES (?,?,?,?)",
                (chat_id, role, text, now))
    cur.execute("UPDATE chats SET updated_at=? WHERE chat_id=?", (now, chat_id))
    conn.commit()
    conn.close()

def get_messages(chat_id: str, limit: int = 10):
    ensure_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT role, text, ts FROM messages WHERE chat_id=? ORDER BY ts DESC LIMIT ?", (chat_id, limit))
    rows = cur.fetchall()
    conn.close()
    return list(reversed(rows))
