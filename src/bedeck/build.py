"""Build the theme files, by rendering each of the package's templates."""

import pathlib

import jinja2

import bedeck.icons
import bedeck.palette


def eza_filenames(icons: bedeck.icons.Icons) -> dict[str, bedeck.icons.Icon]:
  """The icons for eza to match by name, for both files and directories."""
  # eza matches directories by name in filenames too, so it can't tell a file
  # and a directory with the same name apart: leave those names out, so they
  # get eza's built-in icons (which can). It matches directories by extension
  # too, so a name with one of our extensions (e.g. .git) would get that icon
  # instead: those keep the directory's.
  # TODO: check if this can be fixed in eza.
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


def build(icons: pathlib.Path, palette: pathlib.Path, output: pathlib.Path):
  """Render each template (e.g. eza.yml.jinja) to the output directory (as
  eza.yml). They all get the same context, and use what they need of it."""
  colors = bedeck.palette.load(palette)
  icon_colors, data = bedeck.icons.load(icons, colors)
  context = {
    "palette": colors,
    # The palette's colors and the icons file's extra ones: for icons only.
    "icon_colors": icon_colors,
    "icons": data,
    "eza_filenames": eza_filenames(data),
  }
  env = jinja2.Environment(
    loader=jinja2.PackageLoader("bedeck"),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    undefined=jinja2.StrictUndefined,
  )
  env.filters |= {"ord": ord, "lua_string": lua_string}
  output.mkdir(parents=True, exist_ok=True)
  for name in env.list_templates():
    path = output / name.removesuffix(".jinja")
    path.write_text(env.get_template(name).render(context), encoding="utf-8")
    print(f"Wrote {path}")
