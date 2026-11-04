"""Command line interface for bedeck."""

import pathlib
from typing import Annotated

import typer

import bedeck.build
import bedeck.errors
import bedeck.icons
import bedeck.preview


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
Style = Annotated[
  str,
  typer.Option(
    "--style", "-s", help="How the colors are arranged, e.g. in an editor."
  ),
]
Layout = Annotated[
  pathlib.Path | None,
  typer.Option(
    "--layout",
    "-l",
    exists=True,
    dir_okay=False,
    help="A layout file: where to write each file, on top of bedeck's own.",
  ),
]
Flat = Annotated[
  bool,
  typer.Option(
    "--flat",
    "-F",
    help="Write every file straight into the output directory, by its name.",
  ),
]
DryRun = Annotated[
  bool,
  typer.Option(
    "--dry-run", "-n", help="Only print what would be written, not write it."
  ),
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
def preview(theme: Theme) -> None:
  """Print a preview of the theme: mock-ups of a prompt, files, git and more."""
  try:
    bedeck.preview.show(theme)
  except bedeck.errors.BedeckError as error:
    typer.echo(f"bedeck: {error}", err=True)
    raise typer.Exit(1) from error


@app.command()
def build(
  theme: Theme,
  output: Output,
  icons: Icons = None,
  style: Style = "gruvbox",
  layout: Layout = None,
  flat: Flat = False,
  dry_run: DryRun = False,
) -> None:
  """Build the theme files, e.g. eza's theme and mini.icons' config, into the
  output directory where the layout puts them."""
  if flat and layout is not None:
    raise typer.BadParameter("can't be used with --layout", param_hint="--flat")
  try:
    bedeck.build.build(icons, theme, style, output, layout, flat, dry_run)
  except bedeck.errors.BedeckError as error:
    typer.echo(f"bedeck: {error}", err=True)
    raise typer.Exit(1) from error
