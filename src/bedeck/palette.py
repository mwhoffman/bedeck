"""The palette: the named colors that everything is themed with, and the roles
which say what they're used for."""

import pathlib
import re
import tomllib
from typing import NamedTuple

import bedeck.errors


class Palette(NamedTuple):
  colors: dict[str, str]  # {name: hex}
  roles: dict[str, dict[str, str]]  # {group: {role: hex}}


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
  """Read a palette file: returns its colors and its roles, both as hex. A color
  can be given as another color's name (e.g. black = "bg0") rather than as hex,
  and a role (e.g. roles.ui.text) is given as a color's name."""
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
        roles[group][name] = resolved[color]
      else:
        errors.append(f"roles.{group}.{name}: expected the name of a color")

  if errors:
    raise bedeck.errors.BedeckError(
      f"errors in {path}:\n  " + "\n  ".join(errors)
    )
  return Palette(resolved, roles)
