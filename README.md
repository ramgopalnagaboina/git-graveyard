# git-graveyard 🪦

> A respectful tool for digging up dead code.

Every codebase is a graveyard. The auth system you ripped out, the caching layer from 2022, that weird cron job someone deleted in a merge conflict — it's all still in the git history. It's just unfindable, because `git log -S` has the UX of a 1998 Unix man page.

`git-graveyard` is the museum.

## status

Chaotic WIP. Buried so far: `index`, `search`, `interesting`, `show`. Semantic search (embed-and-find) and `serve` (a local web UI) are next.

## install

Requires Python 3.11+.

```sh
pip install git+https://github.com/ramgopalnagaboina/git-graveyard.git
```

## a real example: clicking around in pallets/click

```sh
cd /path/to/click
graveyard index --all          # walks the whole history
graveyard interesting          # the screenshottable view
```

```
🪦 the most interesting corpses (952 total)

═══ biggest deaths ═══
  #943    1686 lines  click.py
        0ed40c88 · Armin Ronacher · 2014-04-26 (11y ago)
        "Split up click into a package"
  #474     519 lines  tests/test_bashcomplete.py
        7029307f · Kai Chen · 2020-10-03 (5y ago)
        "tests for new shell completion system"
  #838     403 lines  docs/_themes/click/static/click.css_t
        dbd40696 · Armin Ronacher · 2015-08-07 (10y ago)
        "Remove shipped theme"

═══ zombie files ═══  (died ≥2x with ≥50 lines each)
  docs/_themes/click/static/click.css_t  2× (799 lines total)
        2015-08-07 → 2018-09-07 · biggest corpse: #838
  src/click/core.py  2× (485 lines total)
        2023-08-19 · biggest corpse: #275

═══ bloodiest files ═══  (most distinct deletions)
  src/click/core.py        89 deaths (1338 lines · biggest: #275)
  CHANGES.rst              36 deaths ( 642 lines · biggest: #694)
  src/click/_compat.py     31 deaths ( 396 lines · biggest: #536)

use graveyard show <id> to see any of these in full.
```

That first row — `#943` — is the day click stopped being a single 1,686-line file and became a package. You can `graveyard show 943` to read the whole original module verbatim.

## the four commands

```sh
graveyard index                   # walk this repo's history (default: last 1000 commits)
graveyard index --all             # everything (slow on big repos)
graveyard index --min-lines 3     # finer-grained corpses

graveyard search 'def setUp'                  # literal substring, case-insensitive
graveyard search --regex 'TODO\(.*\)'         # regex
graveyard search --file core.py 'BaseCommand' # filter by path

graveyard interesting             # the launch view: biggest, zombies, bloodiest

graveyard show 838                # one corpse in full, syntax-highlighted
graveyard show 838 --head 30      # ...truncated
graveyard show 838 --no-code      # ...just the tombstone
```

The index lives in `.graveyard/graveyard.db` inside your repo. We add `.graveyard/` to `.gitignore` for you on first index — no risk of accidentally shipping someone else's git archaeology.

## what counts as a death

Not every `-` in a diff is a death. Renames look like deletions. Refactors look like deletions. A function moved between files is a deletion + addition we should probably leave alone.

Heuristic: **a corpse is a contiguous block of 5+ non-trivial lines that disappeared in a commit and didn't show up (fuzzy-matched) elsewhere in the same commit.** Pygit2's rename detection runs first so file renames don't even reach the heuristic. Defaults are the result of squinting; tune with `--min-lines`.

## roadmap

- **semantic search.** Embed each corpse, embed the query, cosine-similarity. Local model (fastembed), no API calls, no keys. "find me the old rate limiter" should actually surface the old rate limiter, even if the variable was named `throttle_check`.
- **serve.** Local web UI, dark mode (it's a graveyard), search bar, click a corpse to see details. No backend hosted anywhere — `graveyard serve` runs locally against your `.graveyard/graveyard.db`.

## license

MIT. Dig responsibly.
