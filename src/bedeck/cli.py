"""Command line interface for bedeck."""

import pathlib
from typing import Annotated

import typer

import bedeck.icons


app = typer.Typer(no_args_is_help=True, add_completion=True)


@app.callback()
def main() -> None:
  """Tool for generating consistent CLI themes."""


@app.command()
def icons(
  icons: Annotated[
    pathlib.Path,
    typer.Argument(exists=True, dir_okay=False, help="The icons file."),
  ],
  palette: Annotated[
    pathlib.Path,
    typer.Argument(exists=True, dir_okay=False, help="The palette file."),
  ],
) -> None:
  """Print the icons in ICONS, in their colors from PALETTE."""
  try:
    bedeck.icons.show(icons, palette)
  except bedeck.icons.Error as error:
    typer.echo(f"bedeck: {error}", err=True)
    raise typer.Exit(1) from error
