"""Command line interface for bedeck."""

import pathlib
from typing import Annotated

import typer

import bedeck.build
import bedeck.icons


Icons = Annotated[
  pathlib.Path,
  typer.Option(
    "--icons", "-i", exists=True, dir_okay=False, help="The icons file."
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

app = typer.Typer(no_args_is_help=True, add_completion=True)


@app.callback()
def main() -> None:
  """Tool for generating consistent CLI themes."""


@app.command()
def icons(icons: Icons, palette: Palette) -> None:
  """Print the icons in their colors from the palette."""
  try:
    bedeck.icons.show(icons, palette)
  except bedeck.icons.Error as error:
    typer.echo(f"bedeck: {error}", err=True)
    raise typer.Exit(1) from error


@app.command()
def build(
  icons: Icons, palette: Palette, output: Output = pathlib.Path("themes")
) -> None:
  """Build eza's and mini.icons' icon config."""
  try:
    bedeck.build.build(icons, palette, output)
  except bedeck.icons.Error as error:
    typer.echo(f"bedeck: {error}", err=True)
    raise typer.Exit(1) from error
