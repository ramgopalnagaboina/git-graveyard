"""Literal / regex search over the corpses table."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Iterable


@dataclass
class Match:
    corpse: sqlite3.Row
    snippet_lines: list[tuple[int, str, bool]]  # (lineno_in_parent, content, is_match_line)
    truncated: int  # how many additional matching lines were elided


def _build_predicate(query: str, regex: bool, case_sensitive: bool):
    if regex:
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            pat = re.compile(query, flags)
        except re.error as e:
            raise ValueError(f"bad regex: {e}") from e
        return lambda s: pat.search(s) is not None, pat
    needle = query if case_sensitive else query.lower()

    def _has(s: str) -> bool:
        hay = s if case_sensitive else s.lower()
        return needle in hay

    return _has, None  # no regex object for plain mode


def search(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 20,
    regex: bool = False,
    case_sensitive: bool = False,
    file_filter: str | None = None,
    author_filter: str | None = None,
    context: int = 1,
    max_snippet_lines: int = 12,
) -> list[Match]:
    pred, _ = _build_predicate(query, regex, case_sensitive)

    sql = "SELECT * FROM corpses WHERE 1=1"
    params: list = []
    if file_filter:
        sql += " AND file_path LIKE ?"
        params.append(f"%{file_filter}%")
    if author_filter:
        sql += " AND (author_name LIKE ? OR author_email LIKE ?)"
        params.append(f"%{author_filter}%")
        params.append(f"%{author_filter}%")
    sql += " ORDER BY commit_time DESC"

    matches: list[Match] = []
    for row in conn.execute(sql, params):
        code: str = row["code"]
        if not pred(code):
            continue
        match = _build_match(row, pred, context=context, max_lines=max_snippet_lines)
        matches.append(match)
        if len(matches) >= limit:
            break
    return matches


def _build_match(row: sqlite3.Row, pred, *, context: int, max_lines: int) -> Match:
    raw_lines = row["code"].splitlines()
    start_lineno = int(row["start_line"])

    matching_idxs = [i for i, ln in enumerate(raw_lines) if pred(ln)]
    keep: set[int] = set()
    for idx in matching_idxs:
        for offset in range(-context, context + 1):
            j = idx + offset
            if 0 <= j < len(raw_lines):
                keep.add(j)

    if not keep:
        # match was likely on a multi-line pattern crossing newlines (regex)
        # fall back to first lines.
        keep = set(range(min(max_lines, len(raw_lines))))

    keep_sorted = sorted(keep)[:max_lines]
    truncated = max(0, len(matching_idxs) - sum(1 for i in keep_sorted if i in matching_idxs))

    snippet: list[tuple[int, str, bool]] = []
    for i in keep_sorted:
        snippet.append((start_lineno + i, raw_lines[i], i in set(matching_idxs)))
    return Match(corpse=row, snippet_lines=snippet, truncated=truncated)


def highlight(line: str, query: str, regex: bool, case_sensitive: bool) -> str:
    """Return a rich-markup string with matches wrapped in [bold red]…[/]."""
    if regex:
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            pat = re.compile(query, flags)
        except re.error:
            return _escape(line)
        result, last = [], 0
        for m in pat.finditer(line):
            result.append(_escape(line[last : m.start()]))
            result.append(f"[bold red on black]{_escape(m.group(0))}[/bold red on black]")
            last = m.end()
        result.append(_escape(line[last:]))
        return "".join(result)

    if case_sensitive:
        needle = query
        hay_for_search = line
    else:
        needle = query.lower()
        hay_for_search = line.lower()

    out, i = [], 0
    while True:
        j = hay_for_search.find(needle, i)
        if j == -1:
            out.append(_escape(line[i:]))
            break
        out.append(_escape(line[i:j]))
        out.append(f"[bold red on black]{_escape(line[j : j + len(needle)])}[/bold red on black]")
        i = j + len(needle)
    return "".join(out)


def _escape(s: str) -> str:
    return s.replace("[", "\\[")
