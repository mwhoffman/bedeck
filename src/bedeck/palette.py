"""The palette: the named colors that everything is themed with."""

import pathlib
import re
import tomllib

import bedeck.errors


def read_toml(path: pathlib.Path) -> dict:
  try:
    with path.open("rb") as file:
      return tomllib.load(file)
  except tomllib.TOMLDecodeError as error:
    raise bedeck.errors.BedeckError(f"{path}: {error}") from error


def bad_colors(
  section: str,
  colors: dict,
) -> list[str]:
  """An error for each of a section's colors that isn't a hex color."""
  return [
    f"{section}.{name}: expected a color like #rrggbb"
    for name, value in colors.items()
    if not (isinstance(value, str) and re.fullmatch("#[0-9a-fA-F]{6}", value))
  ]


def load(path: pathlib.Path) -> dict[str, str]:
  """Read a palette file: returns its colors, as {name: hex}."""
  colors = read_toml(path).get("colors")
  if not isinstance(colors, dict):
    raise bedeck.errors.BedeckError(f"{path}: expected a colors section")
  if bad := bad_colors("colors", colors):
    raise bedeck.errors.BedeckError(f"errors in {path}:\n  " + "\n  ".join(bad))
  return colors
