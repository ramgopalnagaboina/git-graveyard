# git-graveyard 🪦

> A respectful tool for digging up dead code.

Every codebase is a graveyard. The auth system you ripped out, the caching layer from 2022, that weird cron job someone deleted in a merge conflict — it's all still in the git history. It's just unfindable, because `git log -S` has the UX of a 1998 Unix man page.

`git-graveyard` is the museum.

## status

Chaotic WIP. Currently buried: skeleton + `status`. `index` lands next.

## install

Requires Python 3.11+.

```sh
pip install git+https://github.com/ramgopalnagaboina/git-graveyard.git
```

## use

```sh
cd /path/to/some/repo

graveyard index            # walk history, find every real deletion (last 1000 commits)
graveyard index --all      # walk EVERYTHING (this will take a while)

graveyard search 'rate limit'                 # literal grep over the dead
graveyard search --semantic 'old auth flow'   # embed-and-find (coming soon)

graveyard show 42          # full corpse: code, tombstone, what replaced it
```

The index lives in `.graveyard/graveyard.db` inside your repo. We add `.graveyard/` to `.gitignore` for you on first index — no risk of accidentally shipping someone else's git archaeology.

## what counts as a death

Not every `-` in a diff is a death. Renames look like deletions. Refactors look like deletions. A function moved between files is a deletion + addition we should probably leave alone.

Heuristic: **a corpse is a contiguous block of 5+ non-trivial lines that disappeared in a commit and didn't show up (fuzzy-matched) elsewhere in the same commit.** Tunable; defaults are the result of squinting.

## license

MIT. Dig responsibly.
