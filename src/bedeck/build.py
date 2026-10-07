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


def build(
  icons: pathlib.Path,
  palette: pathlib.Path,
  output: pathlib.Path,
  yes: bool,
) -> None:
  """Render each template (e.g. eza.yml.jinja) to the output directory (as
  eza.yml), asking before overwriting a file unless `yes`. They all get the
  same context, and use what they need of it."""
  colors, roles = bedeck.palette.load(palette)
  icon_colors, data = bedeck.icons.load(icons, colors)
  context = {
    "colors": colors,
    # The palette's colors and the icons file's extra ones: for icons only.
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
