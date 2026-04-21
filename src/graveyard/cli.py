import click

from . import __version__


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="graveyard")
def cli() -> None:
    """🪦 graveyard — browse the code that used to exist in this repo."""


@cli.command()
def status() -> None:
    """Report what's buried here."""
    click.echo("graveyard: 0 corpses")


if __name__ == "__main__":
    cli()
