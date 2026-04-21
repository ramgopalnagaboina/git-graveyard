"""Shared rendering helpers — keep the look-and-feel consistent across commands."""
from __future__ import annotations

import datetime as dt
from pathlib import PurePosixPath

EXT_TO_LEXER: dict[str, str] = {
    ".py": "python", ".pyx": "python", ".pyi": "python",
    ".js": "javascript", ".jsx": "jsx", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "tsx",
    ".go": "go", ".rs": "rust", ".rb": "ruby", ".java": "java", ".kt": "kotlin",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp", ".cc": "cpp",
    ".cs": "csharp", ".php": "php", ".swift": "swift",
    ".sh": "bash", ".bash": "bash", ".zsh": "bash", ".fish": "bash",
    ".html": "html", ".htm": "html", ".css": "css", ".scss": "scss", ".sass": "sass",
    ".md": "markdown", ".rst": "rst", ".tex": "tex",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml", ".ini": "ini",
    ".sql": "sql", ".xml": "xml", ".lua": "lua",
    ".dockerfile": "docker", ".tf": "terraform", ".hcl": "hcl",
}


def lexer_for(path: str) -> str:
    """Best-effort pygments lexer name for a path. Falls back to plain text."""
    p = PurePosixPath(path)
    name = p.name.lower()
    if name in {"dockerfile", "makefile"}:
        return "docker" if name == "dockerfile" else "makefile"
    return EXT_TO_LEXER.get(p.suffix.lower(), "text")


def fmt_date(unix_ts: int) -> str:
    return dt.datetime.fromtimestamp(unix_ts).strftime("%Y-%m-%d")


def fmt_when(unix_ts: int) -> str:
    """Relative-ish timestamp: '3y ago', '2mo ago', '14d ago'."""
    now = dt.datetime.now().timestamp()
    delta = max(0, now - unix_ts)
    days = delta / 86400
    if days < 1:
        return "today"
    if days < 30:
        return f"{int(days)}d ago"
    if days < 365:
        return f"{int(days / 30)}mo ago"
    return f"{int(days / 365)}y ago"
