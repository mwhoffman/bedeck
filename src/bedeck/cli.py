"""Command line interface for bedeck."""

import pathlib
from typing import Annotated

import typer

import bedeck.build
import bedeck.errors
import bedeck.icons


Icons = Annotated[
  pathlib.Path | None,
  typer.Option(
    "--icons",
    "-i",
    exists=True,
    dir_okay=False,
    help="A file of icons, to add to or replace bedeck's own.",
  ),
]
Palette = Annotated[
  pathlib.Path,
  typer.Option(
    "--palette", "-p", exists=True, dir_okay=False, help="The palette file."
  ),
]
Output = Annotated[
  pathlib.Path,
  typer.Option(
    "--output", "-o", file_okay=False, help="The directory to write to."
  ),
]
Yes = Annotated[
  bool,
  typer.Option("--yes", "-y", help="Overwrite existing files without asking."),
]

app = typer.Typer(no_args_is_help=True, add_completion=True)


@app.callback()
def main() -> None:
  """Tool for generating consistent CLI themes."""


@app.command()
def icons(
  palette: Palette,
  icons: Icons = None,
) -> None:
  """Print the icons in their colors from the palette."""
  try:
    bedeck.icons.show(icons, palette)
  except bedeck.errors.BedeckError as error:
    typer.echo(f"bedeck: {error}", err=True)
    raise typer.Exit(1) from error


@app.command()
def build(
  palette: Palette,
  output: Output,
  icons: Icons = None,
  yes: Yes = False,
) -> None:
  """Build the theme files, e.g. eza's theme and mini.icons' config."""
  try:
    bedeck.build.build(icons, palette, output, yes)
  except bedeck.errors.BedeckError as error:
    typer.echo(f"bedeck: {error}", err=True)
    raise typer.Exit(1) from error
