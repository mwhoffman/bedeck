"""The palette: the named colors that everything is themed with, and the roles
which say what they're used for."""

import pathlib
import re
import tomllib
from typing import NamedTuple

import bedeck.errors


# The 16 ANSI colors, in order.
ANSI = [
  "black",
  "red",
  "green",
  "yellow",
  "blue",
  "magenta",
  "cyan",
  "white",
  "bright_black",
  "bright_red",
  "bright_green",
  "bright_yellow",
  "bright_blue",
  "bright_magenta",
  "bright_cyan",
  "bright_white",
]


class Color(str):
  """A color: its hex, which also knows the name it was given by, and its index
  if that's one of the ANSI colors (else None). So a role given as "black" is
  ANSI color 0, but one given as "bg0" isn't, even if they're the same hex."""

  name: str
  ansi: int | None

  def __new__(cls, value: str, name: str):
    color = super().__new__(cls, value)
    color.name = name
    color.ansi = ANSI.index(name) if name in ANSI else None
    return color


class Palette(NamedTuple):
  colors: dict[str, Color]
  roles: dict[str, dict[str, Color]]  # {group: {role: color}}


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


def load(path: pathlib.Path) -> Palette:
  """Read a palette file: returns its colors and its roles. A color can be given
  as another color's name (e.g. black = "bg0") rather than as hex, and a role
  (e.g. roles.ui.text) is given as a color's name."""
  data = read_toml(path)
  colors = data.get("colors")
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
  errors = bad_colors("colors", resolved, expected)

  roles = {}
  for group, entries in data.get("roles", {}).items():
    if not isinstance(entries, dict):
      errors.append(f"roles.{group}: expected a section of roles")
      continue
    roles[group] = {}
    for name, color in entries.items():
      if isinstance(color, str) and color in resolved:
        roles[group][name] = Color(resolved[color], color)
      else:
        errors.append(f"roles.{group}.{name}: expected the name of a color")

  if errors:
    raise bedeck.errors.BedeckError(
      f"errors in {path}:\n  " + "\n  ".join(errors)
    )
  colors = {name: Color(value, name) for name, value in resolved.items()}
  return Palette(colors, roles)
