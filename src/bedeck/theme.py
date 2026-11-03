"""A theme: the named colors that everything is themed with, and the roles which
say what they're used for."""

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


class Theme(NamedTuple):
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


def mix(color: str, into: str, amount: float) -> str:
  """A color (as hex) mixed into another: the amount (0 to 1) is how much of the
  result is the first color."""
  parts = [
    round(b + amount * (a - b))
    for a, b in (
      (int(color[i : i + 2], 16), int(into[i : i + 2], 16)) for i in (1, 3, 5)
    )
  ]
  return "#" + "".join(f"{part:02x}" for part in parts)


def is_role(value: str, groups: dict[str, dict]) -> bool:
  """Whether a value names a role, e.g. ui.text, of the given groups."""
  group, _, name = value.partition(".")
  return group in groups and name in groups[group]


def load(path: pathlib.Path) -> Theme:
  """Read a theme file: returns its colors and its roles. A color can be given
  as another color's name (e.g. black = "bg0") rather than as hex. A role (e.g.
  roles.ui.text) is given as a color's name, as another role's name (e.g.
  ui.dim, so that the two match), or as a mix of one color into another (e.g.
  {mix = "green", into = "bg0", amount = 0.4})."""
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

  # Each group's entries, as given. A role naming another role (e.g. ui.dim) is
  # resolved once all the others are, below.
  entries_by_group = {}
  for group, entries in data.get("roles", {}).items():
    if isinstance(entries, dict):
      entries_by_group[group] = entries
    else:
      errors.append(f"roles.{group}: expected a section of roles")

  roles = {group: {} for group in entries_by_group}
  references = {}
  for group, entries in entries_by_group.items():
    for name, value in entries.items():
      match value:
        case str() if value in resolved:
          roles[group][name] = Color(resolved[value], value)
        case str() if is_role(value, entries_by_group):
          references[f"{group}.{name}"] = value
        case {
          "mix": str() as color,
          "into": str() as into,
          "amount": int() | float() as amount,
        } if color in resolved and into in resolved and 0 <= amount <= 1:
          # The colors' own errors, if any, are reported instead of mixing them.
          if errors:
            mixed = resolved[into]
          else:
            mixed = mix(resolved[color], resolved[into], amount)
          roles[group][name] = Color(mixed, f"{color} into {into}")
        case _:
          errors.append(
            f"roles.{group}.{name}: expected the name of a color or of another "
            'role (e.g. ui.text), or a mix like {mix = "green", into = "bg0", '
            "amount = 0.4}"
          )

  # Follow each reference to a role that's a color, stopping at one already
  # seen (which is a cycle). A role with an error of its own is reported as
  # such, not again by the roles naming it.
  for role, value in references.items():
    seen = {role}
    while value in references and value not in seen:
      seen.add(value)
      value = references[value]
    if value in seen:
      errors.append(f"roles.{role}: names itself, via {value}")
      continue
    group, name = role.split(".", 1)
    target_group, target = value.split(".", 1)
    if target in roles[target_group]:
      roles[group][name] = roles[target_group][target]

  if errors:
    raise bedeck.errors.BedeckError(
      f"errors in {path}:\n  " + "\n  ".join(errors)
    )
  colors = {name: Color(value, name) for name, value in resolved.items()}
  return Theme(colors, roles)
