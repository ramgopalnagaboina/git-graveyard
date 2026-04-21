# git-graveyard 🪦

**A respectful tool for digging up dead code.**

Every codebase is a graveyard. The auth system you ripped out, the caching layer from 2022, that weird cron job someone deleted in a merge conflict — it's all still in the git history. It's just unfindable, because `git log -S` has the UX of a 1998 Unix man page.

`git-graveyard` is the museum.

> Running `graveyard interesting` on [`pallets/click`](https://github.com/pallets/click) surfaces the exact commit where `click.py` stopped being a 1,686-line script and became a package — on April 26, 2014. You can read the whole original file with `graveyard show 943`. That's the pitch.

---

## Status

Chaotic WIP. Shipped: `index`, `search`, `interesting`, `show`. Coming: semantic search, local web UI.

## Install

Requires Python 3.11+.

​```bash
pip install git+https://github.com/ramgopalnagaboina/git-graveyard.git
​```

## Quickstart

​```bash
cd /path/to/any/repo
graveyard index --all          # walks the whole history
graveyard interesting          # the screenshottable view
​```

Sample output from running on `pallets/click`:

​```
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
  src/click/core.py                      2× (485 lines total)
        2023-08-19 · biggest corpse: #275

═══ bloodiest files ═══  (most distinct deletions)
  src/click/core.py        89 deaths (1338 lines · biggest: #275)
  CHANGES.rst              36 deaths ( 642 lines · biggest: #694)
  src/click/_compat.py     31 deaths ( 396 lines · biggest: #536)
​```

## The four commands

**`index`** — walk this repo's history and bury every real deletion.

​```bash
graveyard index                   # default: last 1000 commits
graveyard index --all             # everything (slow on big repos)
graveyard index --min-lines 3     # finer-grained corpses
​```

**`search`** — grep the dead.

​```bash
graveyard search 'def setUp'                  # literal, case-insensitive
graveyard search --regex 'TODO\(.*\)'         # regex
graveyard search --file core.py 'BaseCommand' # filter by path
​```

**`interesting`** — the launch view. Biggest, zombies, bloodiest, all on one screen.

**`show`** — one corpse in full, syntax-highlighted.

​```bash
graveyard show 943                # the original click.py
graveyard show 943 --head 30      # truncate
graveyard show 943 --no-code      # just the tombstone
​```

The index lives in `.graveyard/graveyard.db` inside your repo. `.graveyard/` is added to your `.gitignore` automatically on first run — no risk of accidentally committing someone else's git archaeology.

## What counts as a death

Not every `-` in a diff is a death. Renames look like deletions. Refactors look like deletions. A function moved between files is a deletion + addition we should probably leave alone.

**Heuristic:** a corpse is a contiguous block of 5+ non-trivial lines that disappeared in a commit and didn't show up (fuzzy-matched) elsewhere in the same commit. Pygit2's rename detection runs first, so file renames don't even reach the heuristic. The defaults are the result of squinting at a lot of `click` history; tune with `--min-lines`.

### What's excluded by default

Lockfiles, Jest snapshots, generated code, vendored deps, and minified bundles are filtered at index time — otherwise `yarn.lock` churn drowns out every real finding on a JS repo. The full default list lives in `src/graveyard/excludes.py` and covers `*.lock`, `*.snap`, `**/generated/**`, `**/__generated__/**`, `**/vendor/**`, `**/node_modules/**`, `**/dist/**`, `**/build/**`, `*.min.js`, `*.min.css`, and the common language-specific lockfiles (`package-lock.json`, `Cargo.lock`, `poetry.lock`, `uv.lock`, `Gemfile.lock`, etc.).

Override at index time:

```sh
graveyard index --exclude '**/my-special-gen/**'   # add to defaults
graveyard index --include 'yarn.lock'              # force-include a default-excluded pattern
graveyard index --no-default-excludes              # turn them all off
graveyard status --excludes                        # see what the current graveyard used
```

## Roadmap

**v2 — semantic search.** `graveyard search --semantic "the old rate limiter"` should surface it even if the variable was named `throttle_check`. Local embeddings (fastembed), no API calls, no keys, no cloud.

**v2 — `graveyard serve`.** A local web UI. Dark mode (it's a graveyard). Search bar, click a corpse to see its tombstone. Runs against your local `.graveyard/graveyard.db` — nothing leaves your machine.

## License

MIT. Dig responsibly.
