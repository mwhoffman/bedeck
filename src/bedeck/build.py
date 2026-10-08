"""Build the theme files, by rendering each of the package's templates."""

import pathlib

import jinja2
import rich.prompt

import bedeck.errors
import bedeck.icons
import bedeck.palette


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


def sgr(color: bedeck.palette.Color, ground: str = "fg") -> str:
  """A color as a terminal (SGR) code, as dircolors uses: e.g. 34 for blue, 104
  for a bright blue background, or a 24-bit code if it isn't an ANSI color."""
  offset = 10 if ground == "bg" else 0
  if color.ansi is None:
    rgb = ";".join(str(int(color[i : i + 2], 16)) for i in (1, 3, 5))
    return f"{38 + offset};2;{rgb}"
  return str((30 if color.ansi < 8 else 82) + offset + color.ansi)


def eza(color: bedeck.palette.Color) -> str:
  """A color as eza's theme names it, e.g. LightRed, or else as quoted hex."""
  return f'"{color}"' if color.ansi is None else EZA[color.ansi]


def tmux(color: bedeck.palette.Color) -> str:
  """A color as tmux names it, e.g. color4, or else as hex."""
  return str(color) if color.ansi is None else f"color{color.ansi}"


def zsh(color: bedeck.palette.Color) -> str:
  """A color as zsh's %F{...} takes it: a name (e.g. blue) for the first 8, a
  number (e.g. 11) for the bright ones, or else hex."""
  if color.ansi is None:
    return str(color)
  return NAMES[color.ansi] if color.ansi < 8 else str(color.ansi)


def git(color: bedeck.palette.Color) -> str:
  """A color as git's config names it, e.g. brightgreen, or else as quoted hex."""
  if color.ansi is None:
    return f'"{color}"'
  return ("" if color.ansi < 8 else "bright") + NAMES[color.ansi % 8]


def build(
  icons: pathlib.Path,
  palette: pathlib.Path,
  output: pathlib.Path,
  yes: bool,
) -> None:
  """Render each template (e.g. eza.yml.jinja) to the output directory (as
  eza.yml), asking before overwriting a file unless `yes`. They all get the
  same context, and use what they need of it."""
  theme = bedeck.palette.load(palette)
  colors, roles = theme
  icon_colors, data = bedeck.icons.load(icons, theme)
  context = {
    "colors": colors,
    # The colors icons can have: ANSI ones, file roles and the icons' extras.
    "icon_colors": icon_colors,
    "icons": data,
    "eza_filenames": eza_filenames(data),
  }
  if reserved := roles.keys() & context.keys():
    raise bedeck.errors.BedeckError(
      f"{palette}: roles can't be called {', '.join(sorted(reserved))}"
    )
  # Each group of roles is a name of its own, e.g. ui.text.
  context |= roles
  env = jinja2.Environment(
    loader=jinja2.PackageLoader("bedeck"),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    undefined=jinja2.StrictUndefined,
  )
  env.filters |= {"ord": ord, "lua_string": lua_string}
  env.filters |= {"sgr": sgr, "eza": eza, "tmux": tmux, "zsh": zsh, "git": git}
  # Render them all first, so a problem with one leaves nothing half built.
  files = {
    output / name.removesuffix(".jinja"): env.get_template(name).render(context)
    for name in env.list_templates()
  }
  output.mkdir(parents=True, exist_ok=True)
  for path, text in files.items():
    if path.exists():
      if path.read_bytes() == text.encode("utf-8"):
        print(f"Unchanged {path}")
        continue
      if not yes and not rich.prompt.Confirm.ask(f"Overwrite {path}?"):
        print(f"Skipped {path}")
        continue
    path.write_text(text, encoding="utf-8")
    print(f"Wrote {path}")
