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
Theme = Annotated[
  pathlib.Path,
  typer.Option(
    "--theme", "-t", exists=True, dir_okay=False, help="The theme file."
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
Compare = Annotated[
  bool,
  typer.Option(
    "--compare",
    "-c",
    help="Print only the icons the icons file changes, as old → new.",
  ),
]

app = typer.Typer(no_args_is_help=True, add_completion=True)


@app.callback()
def main() -> None:
  """Tool for generating consistent CLI themes."""


@app.command()
def icons(
  theme: Theme,
  icons: Icons = None,
  compare: Compare = False,
) -> None:
  """Print the icons in their colors from the theme."""
  if compare and icons is None:
    raise typer.BadParameter("needs --icons", param_hint="--compare")
  try:
    bedeck.icons.show(icons, theme, compare)
  except bedeck.errors.BedeckError as error:
    typer.echo(f"bedeck: {error}", err=True)
    raise typer.Exit(1) from error


@app.command()
def build(
  theme: Theme,
  output: Output,
  icons: Icons = None,
  yes: Yes = False,
) -> None:
  """Build the theme files, e.g. eza's theme and mini.icons' config."""
  try:
    bedeck.build.build(icons, theme, output, yes)
  except bedeck.errors.BedeckError as error:
    typer.echo(f"bedeck: {error}", err=True)
    raise typer.Exit(1) from error
