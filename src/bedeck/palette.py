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
  expected: str = "a color like #rrggbb",
) -> list[str]:
  """An error for each of a section's colors that isn't a hex color."""
  return [
    f"{section}.{name}: expected {expected}"
    for name, value in colors.items()
    if not (isinstance(value, str) and re.fullmatch("#[0-9a-fA-F]{6}", value))
  ]


def load(path: pathlib.Path) -> dict[str, str]:
  """Read a palette file: returns its colors, as {name: hex}. A color can be
  given as another color's name (e.g. black = "base") rather than as hex."""
  colors = read_toml(path).get("colors")
  if not isinstance(colors, dict):
    raise bedeck.errors.BedeckError(f"{path}: expected a colors section")
  resolved = {}
  for name, value in colors.items():
    # Follow the names, stopping at one already seen (which is a cycle).
    seen = {name}
    while isinstance(value, str) and value in colors and value not in seen:
      seen.add(value)
      value = colors[value]
    resolved[name] = value
  expected = "a color like #rrggbb or another color's name"
  if bad := bad_colors("colors", resolved, expected):
    raise bedeck.errors.BedeckError(f"errors in {path}:\n  " + "\n  ".join(bad))
  return resolved
