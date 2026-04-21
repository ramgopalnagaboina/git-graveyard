"""Pre-canned 'interesting' queries — the screenshottable views."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

# A "big" deletion for the zombie heuristic — chosen so that gradual
# trimming over many commits doesn't get mistaken for a file dying.
ZOMBIE_BIG_LINES = 50


@dataclass
class BiggestRow:
    id: int
    file_path: str
    line_count: int
    commit_short: str
    commit_subject: str
    author_name: str
    commit_time: int


@dataclass
class ZombieRow:
    file_path: str
    deaths: int
    total_lines: int
    first_death: int  # unix
    last_death: int
    biggest_corpse_id: int


@dataclass
class BloodyRow:
    file_path: str
    deaths: int
    total_lines: int
    biggest_corpse_id: int


def biggest(conn: sqlite3.Connection, limit: int = 5) -> list[BiggestRow]:
    rows = conn.execute(
        """
        SELECT id, file_path, line_count, commit_short, commit_subject,
               author_name, commit_time
        FROM corpses
        ORDER BY line_count DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [
        BiggestRow(
            id=r["id"],
            file_path=r["file_path"],
            line_count=r["line_count"],
            commit_short=r["commit_short"],
            commit_subject=r["commit_subject"] or "",
            author_name=r["author_name"] or "",
            commit_time=r["commit_time"],
        )
        for r in rows
    ]


def zombies(conn: sqlite3.Connection, limit: int = 5) -> list[ZombieRow]:
    rows = conn.execute(
        """
        SELECT
            file_path,
            COUNT(DISTINCT commit_sha) AS deaths,
            SUM(line_count)            AS total_lines,
            MIN(commit_time)           AS first_death,
            MAX(commit_time)           AS last_death
        FROM corpses
        WHERE line_count >= ?
        GROUP BY file_path
        HAVING deaths >= 2
        ORDER BY deaths DESC, total_lines DESC
        LIMIT ?
        """,
        (ZOMBIE_BIG_LINES, limit),
    ).fetchall()

    out: list[ZombieRow] = []
    for r in rows:
        biggest_id = conn.execute(
            "SELECT id FROM corpses WHERE file_path = ? "
            "ORDER BY line_count DESC LIMIT 1",
            (r["file_path"],),
        ).fetchone()["id"]
        out.append(
            ZombieRow(
                file_path=r["file_path"],
                deaths=r["deaths"],
                total_lines=r["total_lines"],
                first_death=r["first_death"],
                last_death=r["last_death"],
                biggest_corpse_id=biggest_id,
            )
        )
    return out


def bloodiest(conn: sqlite3.Connection, limit: int = 5) -> list[BloodyRow]:
    rows = conn.execute(
        """
        SELECT
            file_path,
            COUNT(*)        AS deaths,
            SUM(line_count) AS total_lines
        FROM corpses
        GROUP BY file_path
        ORDER BY deaths DESC, total_lines DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    out: list[BloodyRow] = []
    for r in rows:
        biggest_id = conn.execute(
            "SELECT id FROM corpses WHERE file_path = ? "
            "ORDER BY line_count DESC LIMIT 1",
            (r["file_path"],),
        ).fetchone()["id"]
        out.append(
            BloodyRow(
                file_path=r["file_path"],
                deaths=r["deaths"],
                total_lines=r["total_lines"],
                biggest_corpse_id=biggest_id,
            )
        )
    return out
