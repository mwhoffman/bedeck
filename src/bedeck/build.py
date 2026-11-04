"""Build the theme files, by rendering each of the package's templates."""

import os
import pathlib
import re

import jinja2

import bedeck.errors
import bedeck.icons
import bedeck.theme


# bedeck's templates, and its styles: each is a directory of templates.
TEMPLATES = pathlib.Path(__file__).parent / "data/templates"
STYLES = pathlib.Path(__file__).parent / "data/styles"

# Where each built file goes in the output directory, by default.
LAYOUT = pathlib.Path(__file__).parent / "data/layout.toml"


def eza_filenames(icons: bedeck.icons.Icons) -> dict[str, bedeck.icons.Icon]:
  """The icons for eza to match by name, for both files and directories."""
  # eza matches directories by name in filenames too, so it can't tell a file
  # and a directory with the same name apart: leave those names out, so they
  # get eza's built-in icons (which can). It matches directories by extension
  # too, so a name with one of our extensions (e.g. .git) would get that icon
  # instead: those keep the directory's.
  #
  # A theme can't set the icon of a directory it has no entry for either, so
  # those get eza's built-in ones (custom-folder, or fa-folder_open_o if it's
  # empty) rather than our default.
  # TODO: check if these can be fixed in eza.
  names = icons["file"] | icons["dir"]
  clashes = {
    name
    for name in icons["file"].keys() & icons["dir"].keys()
    if name.rpartition(".")[2] not in icons["ext"] or "." not in name
  }
  return bedeck.icons.by_name(
    {name: icon for name, icon in names.items() if name not in clashes}
  )


def used(entries: dict, text: str, prefix: str) -> dict:
  """The entries that the text refers to as prefix.name, e.g. ui.alert (but not
  ui.alert_bg), so a template can leave out those it doesn't use."""
  return {
    name: value
    for name, value in entries.items()
    if re.search(rf"\b{re.escape(prefix)}\.{re.escape(name)}\b", text)
  }


def lua_string(text: str) -> str:
  """A Lua string literal."""
  return "'" + text.replace("\\", "\\\\").replace("'", "\\'") + "'"


# How each tool names the 16 ANSI colors, in order.
EZA = [
  "Black",
  "Red",
  "Green",
  "Yellow",
  "Blue",
  "Magenta",
  "Cyan",
  "White",
  "DarkGray",
  "LightRed",
  "LightGreen",
  "LightYellow",
  "LightBlue",
  "LightMagenta",
  "LightCyan",
  "LightGray",
]
NAMES = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]


def sgr(color: bedeck.theme.Color, ground: str = "fg") -> str:
  """A color as a terminal (SGR) code, as dircolors uses: e.g. 34 for blue, 104
  for a bright blue background, or a 24-bit code if it isn't an ANSI color."""
  offset = 10 if ground == "bg" else 0
  if color.ansi is None:
    rgb = ";".join(str(int(color[i : i + 2], 16)) for i in (1, 3, 5))
    return f"{38 + offset};2;{rgb}"
  return str((30 if color.ansi < 8 else 82) + offset + color.ansi)


def eza(color: bedeck.theme.Color) -> str:
  """A color as eza's theme names it, e.g. LightRed, or else as quoted hex."""
  return f'"{color}"' if color.ansi is None else EZA[color.ansi]


def tmux(color: bedeck.theme.Color) -> str:
  """A color as tmux names it, e.g. color4, or else as hex."""
  return str(color) if color.ansi is None else f"color{color.ansi}"


def zsh(color: bedeck.theme.Color) -> str:
  """A color as zsh's %F{...} takes it: a name (e.g. blue) for the first 8, a
  number (e.g. 11) for the bright ones, or else hex."""
  if color.ansi is None:
    return str(color)
  return NAMES[color.ansi] if color.ansi < 8 else str(color.ansi)


def git(color: bedeck.theme.Color) -> str:
  """A color as git's config names it, e.g. brightgreen, or else as quoted hex."""
  if color.ansi is None:
    return f'"{color}"'
  return ("" if color.ansi < 8 else "bright") + NAMES[color.ansi % 8]


def fzf(color: bedeck.theme.Color) -> str:
  """A color as fzf's --color takes it: a number (e.g. 11), or else hex."""
  return str(color) if color.ansi is None else str(color.ansi)


def is_dark(theme: bedeck.theme.Theme) -> bool:
  """Whether the theme's background is darker than its text."""

  def brightness(color: str) -> int:
    return sum(int(color[i : i + 2], 16) for i in (1, 3, 5))

  ui = theme.roles["ui"]
  return brightness(ui["background"]) < brightness(ui["text"])


def is_inside(path: str) -> bool:
  """Whether a path (from a layout) stays inside the directory it's relative
  to: it isn't absolute, empty or ".", and has no ".." in it."""
  pure = pathlib.PurePosixPath(path)
  return not pure.is_absolute() and pure.parts != () and ".." not in pure.parts


def layout(
  names: set[str],
  path: pathlib.Path | None,
) -> dict[str, pathlib.PurePosixPath]:
  """Where each of the named files (e.g. eza.yml) goes, relative to the output
  directory: bedeck's layout, with the given one (if any) applied on top. A file
  either sets to false is skipped, so it's left out."""
  paths: dict[str, pathlib.PurePosixPath | None] = {}
  errors = []
  for source in (LAYOUT, path):
    if source is None:
      continue
    for name, value in bedeck.theme.read_toml(source).items():
      if name not in names:
        errors.append(f"{source}: {name}: isn't one of the files built")
      elif value is False:
        paths[name] = None
      elif isinstance(value, str) and is_inside(value):
        paths[name] = pathlib.PurePosixPath(value)
      else:
        errors.append(
          f"{source}: {name}: expected a path inside the output directory, or "
          "false to skip it"
        )
  errors += [f"{LAYOUT}: {name}: missing" for name in sorted(names - paths.keys())]
  chosen = {name: where for name, where in paths.items() if where is not None}
  owners = {}  # the file going to each path
  for name, where in sorted(chosen.items()):
    if where in owners:
      errors.append(f"{owners[where]} and {name} both go to {where}")
    owners[where] = name
  for name, where in sorted(chosen.items()):
    for parent in where.parents:
      if parent in owners:
        errors.append(f"{name} goes inside {parent}, which is {owners[parent]}")
  if errors:
    raise bedeck.errors.BedeckError(
      "errors in the layout:\n  " + "\n  ".join(errors)
    )
  return chosen


def extra_files(
  output: pathlib.Path,
  built: set[pathlib.PurePosixPath],
) -> list[pathlib.PurePosixPath]:
  """The files in the output directory (relative to it) that aren't among those
  built, e.g. ones left from an older layout. Links count as files, and aren't
  followed; .git directories are skipped."""
  extra = []
  for root, dirs, files in os.walk(output):
    dirs[:] = [name for name in dirs if name != ".git"]
    relative = pathlib.PurePosixPath(pathlib.Path(root).relative_to(output))
    # os.walk lists links to directories as directories, but doesn't go in.
    links = [name for name in dirs if (pathlib.Path(root) / name).is_symlink()]
    extra += [
      relative / name
      for name in files + links
      if relative / name not in built
    ]
  return sorted(extra)


def build(
  icons: pathlib.Path | None,
  theme: pathlib.Path,
  style: str,
  output: pathlib.Path,
  layout_file: pathlib.Path | None = None,
  flat: bool = False,
  dry_run: bool = False,
) -> None:
  """Render each template (e.g. eza.yml.jinja) as a file (eza.yml), and write
  it to the output directory: where the layout puts it, or straight into the
  directory if `flat`. Files that are already up to date are left alone, and
  files in the directory that weren't built are listed but not removed. If
  `dry_run`, only print what would be written.

  The templates are bedeck's and those of the style, which is how the colors
  are arranged in e.g. an editor. They all get the same context, and use what
  they need of it."""
  styles = {path.name: path for path in STYLES.iterdir() if path.is_dir()}
  if style not in styles:
    raise bedeck.errors.BedeckError(
      f"unknown style {style}: the styles are {', '.join(sorted(styles))}"
    )
  loaded = bedeck.theme.load(theme)
  colors, roles = loaded
  icon_colors, data = bedeck.icons.load(icons, loaded)
  context = {
    "colors": colors,
    "roles": roles,
    "ansi": bedeck.theme.ANSI,
    "background": "dark" if is_dark(loaded) else "light",
    # The colors icons can have: ANSI ones, file roles and the icons' extras.
    "icon_colors": icon_colors,
    "icons": data,
    "eza_filenames": eza_filenames(data),
  }
  if reserved := roles.keys() & context.keys():
    raise bedeck.errors.BedeckError(
      f"{theme}: roles can't be called {', '.join(sorted(reserved))}"
    )
  # Each group of roles is a name of its own, e.g. ui.text.
  context |= roles
  env = jinja2.Environment(
    loader=jinja2.FileSystemLoader([TEMPLATES, styles[style]]),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    undefined=jinja2.StrictUndefined,
  )
  env.filters |= {"ord": ord, "lua_string": lua_string}
  env.filters |= {"sgr": sgr, "eza": eza, "tmux": tmux, "zsh": zsh, "git": git}
  env.filters |= {"fzf": fzf, "used": used}
  # Templates starting with _ are only included by others, so aren't built.
  names = {
    name.removesuffix(".jinja")
    for name in env.list_templates()
    if not name.startswith("_")
  }
  if flat:
    paths = {name: pathlib.PurePosixPath(name) for name in names}
  else:
    paths = layout(names, layout_file)
  # Render them all first, so a problem with one leaves nothing half built.
  files = {
    where: env.get_template(name + ".jinja").render(context)
    for name, where in sorted(paths.items(), key=lambda item: item[1])
  }
  for where, text in files.items():
    path = output / where
    if path.is_file() and path.read_bytes() == text.encode("utf-8"):
      print(f"Unchanged {path}")
      continue
    if dry_run:
      print(f"Would write {path}")
      continue
    try:
      path.parent.mkdir(parents=True, exist_ok=True)
      path.write_text(text, encoding="utf-8")
    except OSError as error:
      raise bedeck.errors.BedeckError(f"can't write {path}: {error}") from error
    print(f"Wrote {path}")
  if output.is_dir():
    for where in extra_files(output, set(files)):
      print(f"Not built (left as is): {output / where}")
