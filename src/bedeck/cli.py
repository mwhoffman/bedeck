"""Command line interface for bedeck."""

import pathlib
from typing import Annotated

import typer

import bedeck.errors
import bedeck.icons
import bedeck.install


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
Target = Annotated[
  pathlib.Path,
  typer.Option(
    "--target", "-t", file_okay=False, help="The directory to install under."
  ),
]
Yes = Annotated[
  bool,
  typer.Option("--yes", "-y", help="Overwrite existing files without asking."),
]

HOME = pathlib.Path.home()

app = typer.Typer(no_args_is_help=True, add_completion=True)


@app.callback()
def main() -> None:
  """Tool for generating consistent CLI themes."""


@app.command()
def icons(
  icons: Icons,
  palette: Palette,
) -> None:
  """Print the icons in their colors from the palette."""
  try:
    bedeck.icons.show(icons, palette)
  except bedeck.errors.BedeckError as error:
    typer.echo(f"bedeck: {error}", err=True)
    raise typer.Exit(1) from error


@app.command()
def install(
  icons: Icons,
  palette: Palette,
  target: Target = HOME,
  yes: Yes = False,
) -> None:
  """Install the theme files, e.g. eza's theme and mini.icons' config."""
  try:
    bedeck.install.install(icons, palette, target, yes)
  except bedeck.errors.BedeckError as error:
    typer.echo(f"bedeck: {error}", err=True)
    raise typer.Exit(1) from error
