"""
Path filtering for the indexer.

Patterns follow a small subset of gitignore semantics — enough for the
real cases (lockfiles, snapshots, generated, vendored, minified):

  - No '/' in pattern    → fnmatch the basename at any depth
                            (e.g. '*.lock', 'yarn.lock')
  - 'X/**' or '**/X/**'  → match any path with a directory segment named X
                            (e.g. '**/vendor/**', '__snapshots__/**')
  - Anything else        → fnmatch the full path

`--include` acts as a force-include override: a path matching any include
pattern is never excluded, even if it matches an exclude pattern.
"""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass

DEFAULT_EXCLUDES: list[str] = [
    # lockfiles — every dep bump shows up as a giant deletion otherwise
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Cargo.lock",
    "Pipfile.lock",
    "poetry.lock",
    "uv.lock",
    "Gemfile.lock",
    "composer.lock",
    "bun.lockb",
    "*.lock",
    # test snapshots — these aren't code anyone wrote by hand
    "*.snap",
    "__snapshots__/**",
    # generated code
    "**/generated/**",
    "**/__generated__/**",
    "*.generated.*",
    "*_generated.*",
    "*.pb.go",
    "*.pb.py",
    "*.pb.cc",
    # vendored / build outputs
    "**/vendor/**",
    "**/node_modules/**",
    "**/dist/**",
    "**/build/**",
    "**/.next/**",
    "**/target/**",
    # minified
    "*.min.js",
    "*.min.css",
]


_DIR_GLOB_RE = re.compile(r"^(?:\*\*/)?([^/]+)/\*\*$")


@dataclass
class CompiledFilter:
    excludes_basename: list[str]
    excludes_dirs: set[str]
    excludes_other: list[str]
    includes_basename: list[str]
    includes_dirs: set[str]
    includes_other: list[str]
    raw_excludes: list[str]
    raw_includes: list[str]

    def is_excluded(self, path: str) -> bool:
        # explicit include wins over any exclude
        if _matches(path, self.includes_basename, self.includes_dirs, self.includes_other):
            return False
        return _matches(path, self.excludes_basename, self.excludes_dirs, self.excludes_other)


def compile_filter(excludes: list[str], includes: list[str]) -> CompiledFilter:
    eb, ed, eo = _split(excludes)
    ib, id_, io = _split(includes)
    return CompiledFilter(
        excludes_basename=eb,
        excludes_dirs=ed,
        excludes_other=eo,
        includes_basename=ib,
        includes_dirs=id_,
        includes_other=io,
        raw_excludes=list(excludes),
        raw_includes=list(includes),
    )


def _split(patterns: list[str]) -> tuple[list[str], set[str], list[str]]:
    basename: list[str] = []
    dirs: set[str] = set()
    other: list[str] = []
    for p in patterns:
        if "/" not in p:
            basename.append(p)
            continue
        m = _DIR_GLOB_RE.match(p)
        if m:
            dirs.add(m.group(1))
            continue
        other.append(p)
    return basename, dirs, other


def _matches(
    path: str, basename_globs: list[str], dir_segments: set[str], other_globs: list[str]
) -> bool:
    parts = path.split("/")
    base = parts[-1]
    for g in basename_globs:
        if fnmatch.fnmatchcase(base, g):
            return True
    if dir_segments:
        for seg in parts[:-1]:
            if seg in dir_segments:
                return True
    for g in other_globs:
        if fnmatch.fnmatchcase(path, g):
            return True
    return False


def resolve(
    user_excludes: list[str],
    user_includes: list[str],
    *,
    use_defaults: bool,
) -> CompiledFilter:
    excludes = (list(DEFAULT_EXCLUDES) if use_defaults else []) + list(user_excludes)
    return compile_filter(excludes, list(user_includes))
