from __future__ import annotations

import datetime as dt
from pathlib import Path

import click
from rich.console import Console

from . import __version__
from . import db as dbmod
from . import indexer

console = Console(stderr=False)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="graveyard")
def cli() -> None:
    """🪦 graveyard — browse the code that used to exist in this repo."""


def _db_path_for_cwd() -> tuple[Path, Path]:
    repo_root = indexer.find_repo_root(Path.cwd())
    return repo_root, repo_root / ".graveyard" / "graveyard.db"


@cli.command()
def status() -> None:
    """Report what's buried here."""
    try:
        repo_root, db_path = _db_path_for_cwd()
    except FileNotFoundError as e:
        raise click.ClickException(str(e))
    if not db_path.exists():
        click.echo("graveyard: 0 corpses (run `graveyard index` to dig)")
        return
    conn = dbmod.connect(db_path)
    n = dbmod.count_corpses(conn)
    click.echo(f"graveyard: {n} corpse{'s' if n != 1 else ''}")
    click.echo(f"  db: {db_path.relative_to(repo_root)}")


@cli.command()
@click.option(
    "--limit",
    type=int,
    default=1000,
    show_default=True,
    help="Walk at most this many commits (newest first). Use --all to remove the cap.",
)
@click.option("--all", "all_commits", is_flag=True, help="Walk every commit. Slow on large repos.")
@click.option(
    "--min-lines",
    type=int,
    default=5,
    show_default=True,
    help="A deletion must have at least this many non-trivial lines to count as a corpse.",
)
@click.option(
    "--rebuild/--no-rebuild",
    default=True,
    help="Wipe the existing graveyard before indexing (default: yes).",
)
def index(limit: int, all_commits: bool, min_lines: int, rebuild: bool) -> None:
    """Walk this repo's history and bury every real deletion."""
    try:
        repo_root, db_path = _db_path_for_cwd()
    except FileNotFoundError as e:
        raise click.ClickException(str(e))

    indexer.ensure_gitignored(repo_root)
    conn = dbmod.connect(db_path)
    dbmod.init(conn)
    if rebuild:
        dbmod.reset(conn)

    cap = None if all_commits else limit
    cap_label = "all commits" if cap is None else f"last {cap} commit{'s' if cap != 1 else ''}"
    console.print(
        f"[magenta]🪦 digging…[/magenta] [dim]({cap_label}, min {min_lines} lines)[/dim]"
    )

    last_print = 0

    def progress(stats: indexer.IndexStats, commit) -> None:
        nonlocal last_print
        # Print every 50 commits to avoid spam but keep the impression of progress
        if stats.commits_walked - last_print >= 50:
            last_print = stats.commits_walked
            ts = dt.datetime.fromtimestamp(commit.commit_time).strftime("%Y-%m-%d")
            console.print(
                f"  [dim]{stats.commits_walked} commits · {stats.corpses} corpses · "
                f"at {str(commit.id)[:8]} ({ts})[/dim]"
            )

    stats = indexer.index_repo(
        repo_root, conn, limit=cap, min_lines=min_lines, on_commit=progress
    )

    dbmod.set_meta(conn, "indexed_at", dt.datetime.now().isoformat(timespec="seconds"))
    dbmod.set_meta(conn, "commits_walked", str(stats.commits_walked))
    dbmod.set_meta(conn, "corpses", str(stats.corpses))

    console.print()
    console.print(
        f"[green]🪦 buried {stats.corpses} corpse(s)[/green] from "
        f"{stats.commits_walked} commit(s)."
    )
    if stats.commits_skipped_merge:
        console.print(f"   [dim]({stats.commits_skipped_merge} merge(s) skipped)[/dim]")
    console.print(f"   [dim]db: {db_path.relative_to(repo_root)}[/dim]")


if __name__ == "__main__":
    cli()
