"""
Walk a git history and find every real deletion.

A "real" deletion is a contiguous block of N+ non-trivial lines that
disappeared in a commit and didn't show up (fuzzy-matched) elsewhere
in that same commit. Renames are skipped via pygit2's find_similar().
Merges are skipped entirely — they're not where lines truly die.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

import pygit2

# Anything below this Jaccard similarity (normalized lines) means
# the deletion isn't a re-appearance of the same code elsewhere.
MOVE_SIMILARITY_THRESHOLD = 0.8


@dataclass
class IndexStats:
    commits_walked: int = 0
    commits_skipped_merge: int = 0
    corpses: int = 0


def find_repo_root(start: Path) -> Path:
    p = start.resolve()
    for cand in [p, *p.parents]:
        if (cand / ".git").exists():
            return cand
    raise FileNotFoundError(f"not inside a git repository: {start}")


def ensure_gitignored(repo_root: Path) -> None:
    """Append `.graveyard/` to the repo's .gitignore if it isn't there."""
    gi = repo_root / ".gitignore"
    line = ".graveyard/"
    existing = gi.read_text() if gi.exists() else ""
    if any(l.strip() == line for l in existing.splitlines()):
        return
    suffix = "" if existing.endswith("\n") or existing == "" else "\n"
    gi.write_text(existing + suffix + line + "\n")


def _normalize(lines: list[str]) -> list[str]:
    """Strip trailing whitespace; collapse runs of whitespace; drop blanks."""
    out = []
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        out.append(re.sub(r"\s+", " ", s))
    return out


def _collect_added_blocks(diff) -> list[set[str]]:
    """Every contiguous '+' run in the diff, normalized into a line-set."""
    blocks: list[set[str]] = []
    for patch in diff:
        if patch.delta.is_binary:
            continue
        for hunk in patch.hunks:
            run: list[str] = []
            for line in hunk.lines:
                if line.origin == "+":
                    run.append(line.content)
                else:
                    if run:
                        s = set(_normalize(run))
                        if s:
                            blocks.append(s)
                        run = []
            if run:
                s = set(_normalize(run))
                if s:
                    blocks.append(s)
    return blocks


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _is_moved(deletion_norm: set[str], added_blocks: list[set[str]]) -> bool:
    if not deletion_norm:
        return False
    return any(
        _jaccard(deletion_norm, b) >= MOVE_SIMILARITY_THRESHOLD for b in added_blocks
    )


def _extract_deletion_runs(
    hunk, min_lines: int
) -> Iterator[tuple[int, int, list[str]]]:
    """Yield (start_lineno_in_parent, end_lineno_in_parent, raw_lines)."""
    cur: list[tuple[int, str]] = []

    def flush():
        if not cur:
            return None
        raw = [c for _, c in cur]
        if len(_normalize(raw)) < min_lines:
            return None
        return cur[0][0], cur[-1][0], raw

    for line in hunk.lines:
        if line.origin == "-":
            # old_lineno is 1-based in the parent file
            cur.append((line.old_lineno, line.content))
        else:
            emitted = flush()
            if emitted:
                yield emitted
            cur = []
    emitted = flush()
    if emitted:
        yield emitted


def _is_rename(patch) -> bool:
    # pygit2 changed how status enums are exposed across versions; status_char is stable.
    try:
        return patch.delta.status_char() in ("R", "C")  # rename or copy
    except Exception:
        return False


def index_repo(
    repo_root: Path,
    conn: sqlite3.Connection,
    *,
    limit: int | None,
    min_lines: int,
    on_commit: Callable[[IndexStats, "pygit2.Commit"], None] | None = None,
) -> IndexStats:
    repo = pygit2.Repository(str(repo_root))
    if repo.is_empty:
        return IndexStats()
    if repo.head_is_unborn:
        return IndexStats()

    walker = repo.walk(repo.head.target, pygit2.GIT_SORT_TIME)
    stats = IndexStats()
    cur = conn.cursor()

    insert_sql = (
        "INSERT INTO corpses ("
        "commit_sha, commit_short, commit_time, commit_subject, commit_message, "
        "author_name, author_email, parent_sha, file_path, "
        "start_line, end_line, line_count, code"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )

    for commit in walker:
        if limit is not None and stats.commits_walked >= limit:
            break
        stats.commits_walked += 1
        if on_commit:
            on_commit(stats, commit)

        # Merges produce diffs that double-count work; skip them.
        if len(commit.parents) > 1:
            stats.commits_skipped_merge += 1
            continue
        if not commit.parents:
            # root commit — only additions, no deaths
            continue

        parent = commit.parents[0]
        try:
            diff = repo.diff(parent, commit)
        except Exception:
            continue

        # Mark renames as renames instead of delete+add. 50% sim is libgit2 default.
        try:
            diff.find_similar()
        except Exception:
            pass

        added_blocks = _collect_added_blocks(diff)
        rows: list[tuple] = []

        subject = commit.message.split("\n", 1)[0].strip() if commit.message else ""

        for patch in diff:
            if patch.delta.is_binary:
                continue
            if _is_rename(patch):
                continue
            old_path = patch.delta.old_file.path
            for hunk in patch.hunks:
                for start, end, raw_lines in _extract_deletion_runs(hunk, min_lines):
                    deletion_norm = set(_normalize(raw_lines))
                    if _is_moved(deletion_norm, added_blocks):
                        continue
                    code = "".join(raw_lines)
                    rows.append((
                        str(commit.id),
                        str(commit.id)[:8],
                        int(commit.commit_time),
                        subject,
                        commit.message or "",
                        commit.author.name or "",
                        commit.author.email or "",
                        str(parent.id),
                        old_path,
                        start,
                        end,
                        end - start + 1,
                        code,
                    ))
                    stats.corpses += 1

        if rows:
            cur.executemany(insert_sql, rows)
            conn.commit()

    return stats
