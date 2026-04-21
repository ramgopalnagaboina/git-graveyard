import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS corpses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commit_sha       TEXT    NOT NULL,
    commit_short     TEXT    NOT NULL,
    commit_time      INTEGER NOT NULL,
    commit_subject   TEXT,
    commit_message   TEXT,
    author_name      TEXT,
    author_email     TEXT,
    parent_sha       TEXT,
    file_path        TEXT    NOT NULL,
    start_line       INTEGER NOT NULL,
    end_line         INTEGER NOT NULL,
    line_count       INTEGER NOT NULL,
    code             TEXT    NOT NULL,
    -- reserved for v2 (semantic search)
    embedding        BLOB,
    embedding_model  TEXT
);

CREATE INDEX IF NOT EXISTS idx_corpses_commit ON corpses(commit_sha);
CREATE INDEX IF NOT EXISTS idx_corpses_path   ON corpses(file_path);
CREATE INDEX IF NOT EXISTS idx_corpses_time   ON corpses(commit_time);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    cur = conn.execute("SELECT version FROM schema_version LIMIT 1")
    row = cur.fetchone()
    if row is None:
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
    conn.commit()


def reset(conn: sqlite3.Connection) -> None:
    """Wipe corpses + meta but keep the schema."""
    conn.execute("DELETE FROM corpses")
    conn.execute("DELETE FROM meta")
    conn.commit()


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()


def count_corpses(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) AS n FROM corpses").fetchone()["n"]
