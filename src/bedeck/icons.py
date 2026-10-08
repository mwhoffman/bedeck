"""Icons, and their colors, for directories, file names and extensions."""

import json
import pathlib
import urllib.request
from typing import NamedTuple

import rich.columns
import rich.console
import rich.text

import bedeck.errors
import bedeck.palette


# bedeck's own icons, which an icons file given to it adds to or replaces.
ICONS = pathlib.Path(__file__).parent / "icons.toml"

CACHE = pathlib.Path.home() / ".cache/bedeck"
NERD_FONTS = "v3.5.1"  # the version of the installed fonts
GLYPHNAMES = (
  "https://raw.githubusercontent.com/ryanoasis/nerd-fonts/"
  f"{NERD_FONTS}/glyphnames.json"
)

# The sections of an icons file and their titles, in the order they're shown.
SECTIONS = {
  "default": "Defaults",
  "dir": "Directories",
  "file": "File names",
  "ext": "Extensions",
  "filetype": "Filetypes",
}
# The default whose color each section's entries get if they don't give one.
DEFAULTS = {"dir": "dir", "file": "file", "ext": "file", "filetype": "file"}
# How the names in a section are shown, if not as they are.
LABELS = {"dir": "{}/", "ext": "*.{}"}


class Icon(NamedTuple):
  glyph: str
  color: str  # the name of one of the icons' colors


Icons = dict[str, dict[str, Icon]]


def glyphs() -> dict[str, str]:
  """Nerd Font glyphs by name (e.g. oct-gear), downloaded once and cached."""
  cached = CACHE / f"glyphnames-{NERD_FONTS}.json"
  if not cached.exists():
    try:
      with urllib.request.urlopen(GLYPHNAMES) as response:
        data = response.read()
    except OSError as error:
      raise bedeck.errors.BedeckError(
        f"couldn't download {GLYPHNAMES}: {error}"
      ) from error
    CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(data)
  names = json.loads(cached.read_text(encoding="utf-8"))
  return {
    name: value["char"] for name, value in names.items() if name != "METADATA"
  }


def by_name(entries: dict) -> dict:
  return dict(sorted(entries.items(), key=lambda entry: entry[0].lower()))


def read(path: pathlib.Path) -> dict[str, dict]:
  """Read an icons file, checking it only has the sections it can."""
  data = bedeck.palette.read_toml(path)
  sections = (*SECTIONS, "extra-colors")
  unknown = [
    name
    for name, value in data.items()
    if name not in sections or not isinstance(value, dict)
  ]
  if unknown:
    raise bedeck.errors.BedeckError(
      f"{path}: expected the sections {', '.join(sections)}, "
      f"not {', '.join(unknown)}"
    )
  return data


def load(
  icons: pathlib.Path | None,
  palette: bedeck.palette.Palette,
) -> tuple[dict[str, str], Icons]:
  """Read bedeck's icons and then an icons file (if given), whose entries add to
  or replace bedeck's. Returns the colors the icons can have, as {name: hex},
  and the icons, as {section: {name: Icon}} with the sections in SECTIONS' order
  and their entries sorted by name. The colors are the ANSI ones, the palette's
  file roles (e.g. file.media) and the icons' extra ones."""
  data: dict[str, dict] = {}
  source = {}  # the file each entry came from, for reporting errors in it
  errors: dict[pathlib.Path, list[str]] = {}
  for path in (ICONS, icons):
    if path is None:
      continue
    for section, entries in read(path).items():
      data.setdefault(section, {}).update(entries)
      source |= {(section, name): path for name in entries}
      if section == "extra-colors" and (
        bad := bedeck.palette.bad_colors(section, entries)
      ):
        errors[path] = bad

  def error(section: str, name: str, message: str) -> None:
    file = source.get((section, name), ICONS)
    errors.setdefault(file, []).append(f"{section}.{name}: {message}")

  extra = data.get("extra-colors", {})
  colors: dict[str, str] = {
    name: palette.colors[name] for name in bedeck.palette.ANSI
  }
  colors |= {
    f"file.{name}": color
    for name, color in palette.roles.get("file", {}).items()
  }
  # The palette's color is used for an extra one if it has one of that name.
  colors |= {
    name: palette.colors.get(name, color) for name, color in extra.items()
  }
  names = glyphs()

  for name in sorted(
    {*DEFAULTS.values(), "noext"} - data.get("default", {}).keys()
  ):
    error("default", name, "missing")

  result: Icons = {section: {} for section in SECTIONS}
  inherited = {}  # each default's color, for entries that don't give one
  for section in SECTIONS:
    for name, value in by_name(data.get(section, {})).items():
      match value:
        case [str() as icon, str() as color]:
          pass
        case str() as icon if section != "default":
          color = inherited.get(DEFAULTS[section])
        case _:
          error(section, name, "expected an icon or [icon, color]")
          continue
      if section == "default":
        inherited[name] = color
      glyph = icon if len(icon) == 1 else names.get(icon)
      if glyph is None:
        error(section, name, f"unknown icon {icon}")
      if color is None:
        continue  # its default is missing or malformed: an error already
      if color not in colors:
        kind = (
          "isn't an ANSI color" if color in palette.colors else "is unknown"
        )
        error(section, name, f"the color {color} {kind}")
      elif glyph is not None:
        result[section][name] = Icon(glyph, color)

  if errors:
    raise bedeck.errors.BedeckError(
      "\n".join(
        f"errors in {path}:\n  " + "\n  ".join(messages)
        for path, messages in errors.items()
      )
    )
  return colors, result


def show(
  icons: pathlib.Path | None,
  palette: pathlib.Path,
) -> None:
  """Print each section's icons in their colors, wrapped into columns that line
  up across the sections."""
  # The glyph is followed by spaces since kitty only draws an icon wider than a
  # cell if it is.
  colors, data = load(icons, bedeck.palette.load(palette))
  sections = {
    section: [
      rich.text.Text.assemble(
        (glyph, colors[color]), "  ", LABELS.get(section, "{}").format(name)
      )
      for name, (glyph, color) in entries.items()
    ]
    for section, entries in data.items()
    if entries
  }
  width = max(cell.cell_len for cells in sections.values() for cell in cells)
  console = rich.console.Console(highlight=False)
  for section, cells in sections.items():
    console.print(f"\n{SECTIONS[section]} ({len(cells)})", style="bold")
    console.print(rich.columns.Columns(cells, width=width, column_first=True))
