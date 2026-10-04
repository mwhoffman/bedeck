#!/usr/bin/env python3
"""Tools for data/icons.txt, the icons (and their colors) we want for
directories, file names and extensions.

Usage:
  icons.py compare [--refresh]
      Show each entry's icon from nvim-web-devicons, mini.icons and eza next to
      ours, both in our color (ours) and in the color eza gives the file name
      (ours-eza). Pipe it to `less -R` since it's long.
  icons.py seed [--force] [--refresh]
      Write a first data/icons.txt with every entry any of those know, using
      eza's icon, else mini.icons', else devicons'.

devicons, mini.icons, Neovim (whose filetype detection mini.icons uses),
gruvbox.nvim (for mini.icons' colors) and Nerd Fonts (for the icons' names)
are read from their source, which is downloaded and cached in
~/.cache/cli-themes; --refresh downloads it again. eza's icons and colors come
from running the installed eza on sample files, with the current LS_COLORS and
eza theme.
"""

import json
import pathlib
import re
import subprocess
import sys
import tempfile
import urllib.request
from typing import NoReturn


ROOT = pathlib.Path(__file__).resolve().parent
ICONS = ROOT / "data/icons.txt"
CACHE = pathlib.Path.home() / ".cache/cli-themes"

GITHUB = "https://raw.githubusercontent.com"
NERD_FONTS = "v3.5.1"  # the version of the installed fonts

# The files read from each project's source, and the ref (branch or tag) to read
# them from.
SOURCES = {
    "glyphnames.json": (
        "ryanoasis/nerd-fonts", NERD_FONTS, "glyphnames.json"),
    "devicons-filename.lua": (
        "nvim-tree/nvim-web-devicons", "master",
        "lua/nvim-web-devicons/default/icons_by_filename.lua"),
    "devicons-extension.lua": (
        "nvim-tree/nvim-web-devicons", "master",
        "lua/nvim-web-devicons/default/icons_by_file_extension.lua"),
    "devicons-os.lua": (
        "nvim-tree/nvim-web-devicons", "master",
        "lua/nvim-web-devicons/default/icons_by_operating_system.lua"),
    "devicons-de.lua": (
        "nvim-tree/nvim-web-devicons", "master",
        "lua/nvim-web-devicons/default/icons_by_desktop_environment.lua"),
    "devicons-wm.lua": (
        "nvim-tree/nvim-web-devicons", "master",
        "lua/nvim-web-devicons/default/icons_by_window_manager.lua"),
    "mini-icons.lua": (
        "nvim-mini/mini.icons", "main", "lua/mini/icons.lua"),
    "neovim-filetype.lua": (
        "neovim/neovim", "stable", "runtime/lua/vim/filetype.lua"),
    "neovim-detect.lua": (
        "neovim/neovim", "stable", "runtime/lua/vim/filetype/detect.lua"),
    "gruvbox.lua": (
        "ellisonleao/gruvbox.nvim", "main", "lua/gruvbox.lua"),
}

KINDS = ("dir", "file", "ext")
# The defaults data/icons.txt can set: for files with an extension nothing
# knows, files with no extension, and directories.
DEFAULTS = ("file", "noext", "dir")
TITLES = {"dir": "Directories", "file": "File names", "ext": "Extensions"}

# Seed colors for some files, from the choices made for nvim so far. Directories
# are dark blue (like ls), and other names match by (lowercase) name or by
# extension.
SEED_COLORS = {
    "plain": {
        "names": ["brewfile", "config", "gnumakefile", "justfile", "makefile",
                  "readme"],
        "extensions": ["cfg", "conf", "editorconfig", "ini", "log", "markdown",
                       "md", "pylintrc", "txt"],
    },
    "dark-yellow": {  # eza's list of compiled files
        "names": [],
        "extensions": ["a", "bundle", "class", "cma", "cmi", "cmo", "cmx",
                       "dll", "dylib", "elc", "elf", "ko", "lib", "o", "obj",
                       "pyc", "pyd", "pyo", "so", "zwc"],
    },
    "green": {  # eza's list of shell scripts, plus zsh-theme
        "names": [],
        "extensions": ["awk", "bash", "bats", "csh", "fish", "ksh", "nu", "sh",
                       "shell", "zsh", "zsh-theme"],
    },
}

# The colors a first data/icons.txt defines: gruvbox's (dark) palette.
SEED_PALETTE = {
    "plain": "#ebdbb2", "grey": "#928374",
    "red": "#fb4934", "green": "#b8bb26", "yellow": "#fabd2f",
    "blue": "#83a598", "purple": "#d3869b", "aqua": "#8ec07c",
    "orange": "#fe8019",
    "dark-red": "#cc241d", "dark-green": "#98971a", "dark-yellow": "#d79921",
    "dark-blue": "#458588", "dark-purple": "#b16286", "dark-aqua": "#689d6a",
    "dark-orange": "#d65d0e",
}


def fail(message) -> NoReturn:
  sys.exit(f"icons.py: {message}")


def fetch(name, refresh):
  """Return the text of one of SOURCES (or eza's icons.rs), from the cache or
  downloaded."""
  if name == "eza-icons.rs":
    repo, ref, path = ("eza-community/eza", eza_version(),
                       "src/output/icons.rs")
  else:
    repo, ref, path = SOURCES[name]
  cached = CACHE / f"{ref}-{name}".replace("/", "-")
  if refresh or not cached.exists():
    url = f"{GITHUB}/{repo}/{ref}/{path}"
    try:
      with urllib.request.urlopen(url) as response:
        text = response.read().decode()
    except OSError as error:
      fail(f"couldn't download {url}: {error}")
    CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_text(text, encoding="utf-8")
  return cached.read_text(encoding="utf-8")


def eza_version():
  # The second line of `eza --version` is e.g. "v0.23.5 [+git]".
  out = subprocess.run(["eza", "--version"], capture_output=True, text=True,
                       check=True).stdout
  return out.splitlines()[1].split()[0]


def lua_table(source, start):
  """Return the body of the Lua table starting with the line `start`, up to
  the next line that is just a closing brace."""
  match = re.search(rf"^{re.escape(start)}\n(.*?)^\}}", source,
                    re.MULTILINE | re.DOTALL)
  if not match:
    fail(f"couldn't find the table {start!r}")
  return match.group(1)


# A Lua table key: ['x'], ["x"] or x.
LUA_KEY = r"""(?:\['([^']+)'\]|\["([^"]+)"\]|([\w.+~-]+))"""


def lua_key(match):
  return match.group(1) or match.group(2) or match.group(3)


class Glyphs:
  """Nerd Font glyphs by name (e.g. oct-gear), and names by glyph."""

  def __init__(self, refresh):
    data = json.loads(fetch("glyphnames.json", refresh))
    self.by_name = {name: chr(int(value["code"], 16))
                    for name, value in data.items()
                    if isinstance(value, dict) and "code" in value}
    self.by_glyph = {}
    for name in sorted(self.by_name):
      self.by_glyph.setdefault(self.by_name[name], name)

  def glyph(self, icon):
    """The glyph for an icon given by name or as a codepoint (U+F423)."""
    codepoint = re.fullmatch(r"U\+([0-9A-Fa-f]{4,6})", icon)
    if codepoint:
      return chr(int(codepoint.group(1), 16))
    return self.by_name.get(icon)

  def name(self, glyph):
    return self.by_glyph.get(glyph) or f"U+{ord(glyph):04X}"


class Devicons:
  """nvim-web-devicons' icons, looked up like its get_icon (which by default
  looks up extensions in one table of every icon, e.g. so *.gemfile gets
  Gemfile's icon)."""

  def __init__(self, refresh):
    self.filename = self.parse(fetch("devicons-filename.lua", refresh))
    self.extension = self.parse(fetch("devicons-extension.lua", refresh))
    self.all = {}
    for name in ("devicons-filename.lua", "devicons-extension.lua",
                 "devicons-os.lua", "devicons-de.lua", "devicons-wm.lua"):
      self.all.update(self.parse(fetch(name, refresh), required=False))

  @staticmethod
  def parse(source, required=True):
    entries = {}
    for match in re.finditer(
            LUA_KEY + r'\s*=\s*\{\s*icon\s*=\s*"([^"]*)",\s*'
            r'color\s*=\s*"(#[0-9A-Fa-f]{6})"', source):
      entries[lua_key(match).lower()] = (match.group(4),
                                         match.group(5).lower())
    if required and not entries:
      fail("couldn't parse devicons' icons")
    return entries

  def get(self, kind, name):
    if kind == "dir":
      return None
    if kind == "ext":
      name = "x." + name
    name = name.lower()
    found = self.all.get(name)
    # Then each extension, e.g. for a.tar.gz: tar.gz then gz.
    ext = name
    while found is None and "." in ext:
      ext = ext.split(".", 1)[1]
      found = self.all.get(ext)
    return found


class MiniIcons:
  """mini.icons' icons (with gruvbox's colors), looked up like its get, using
  Neovim's filetype detection by file name and extension."""

  def __init__(self, refresh):
    source = fetch("mini-icons.lua", refresh)
    self.directory = self.parse(lua_table(source, "H.directory_icons = {"))
    self.extension = self.parse(lua_table(source, "H.extension_icons = {"))
    self.file = self.parse(lua_table(source, "H.file_icons = {"))
    self.filetype = self.parse(lua_table(source, "H.filetype_icons = {"))

    # Neovim's filetypes by extension and file name (skipping those found
    # by a function, e.g. from the file's contents).
    detect = self.detect_defaults(fetch("neovim-detect.lua", refresh))
    source = fetch("neovim-filetype.lua", refresh)
    self.ft_extension = self.parse_filetypes(
        lua_table(source, "local extension = {"), detect)
    self.ft_filename = self.parse_filetypes(
        lua_table(source, "local filename = {"), detect)

    self.colors = self.gruvbox_colors(fetch("gruvbox.lua", refresh))

  @staticmethod
  def parse(body):
    # Entries are icons ({ glyph = 'x', hl = 'MiniIconsBlue' }) or the
    # name of a filetype to use the icon of.
    entries = {}
    for match in re.finditer(
            r"^\s*" + LUA_KEY + r"\s*=\s*(?:\{\s*glyph\s*=\s*'([^']*)',"
            r"\s*hl\s*=\s*'(\w+)'\s*\}|'([^']*)')", body, re.MULTILINE):
      entries[lua_key(match)] = (
          (match.group(4), match.group(5)) if match.group(4) is not None
          else match.group(6))
    return entries

  @staticmethod
  def detect_defaults(source):
    """The filetype each of Neovim's detect functions returns by default
    (i.e. for an empty file): the last one it returns."""
    defaults = {}
    for match in re.finditer(r"^function M\.(\w+)\((.*?)(?=^function M\.|\Z)",
                             source, re.MULTILINE | re.DOTALL):
      # The last quoted name on the last line returning one, e.g. from
      # "return vim.g.filetype_md or 'markdown'".
      returns = re.findall(r"^\s*return\b.*'([\w.-]+)'[^'\n]*$",
                           match.group(2), re.MULTILINE)
      if returns:
        defaults[match.group(1)] = returns[-1]
    # Shell types made by a helper (e.g. M.bash = sh_with('bash')), which
    # are all the sh filetype.
    for name in re.findall(r"^M\.(\w+) = sh_with\(", source, re.MULTILINE):
      defaults[name] = "sh"
    return defaults

  @staticmethod
  def parse_filetypes(body, detect):
    """Filetypes by key, either given directly or found by one of Neovim's
    detect functions (using its default), or by detect_line1 or detect_seq
    (using their last filetype, which is their default); others (e.g.
    inline functions) are skipped."""
    filetypes = {}
    for match in re.finditer(
            r"^\s*" + LUA_KEY + r"\s*=\s*(?:'([^']+)'|detect\.(\w+)|"
            r"(?:detect_line1|detect_seq)\((.*)\)),\s*$", body, re.MULTILINE):
      filetype = match.group(4) or detect.get(match.group(5))
      if match.group(6):
        quoted = re.findall(r"'([\w.-]+)'", match.group(6))
        filetype = quoted[-1] if quoted else None
      if filetype:
        filetypes[lua_key(match)] = filetype
    return filetypes

  @staticmethod
  def gruvbox_colors(source):
    """gruvbox's (dark) colors for mini.icons' highlight groups."""
    palette = dict(re.findall(r'^\s*(\w+) = "(#[0-9a-f]{6})"', source,
                              re.MULTILINE))
    dark = re.search(r"\bdark = \{(.*?)\}", source, re.DOTALL)
    if not dark:
      fail("couldn't find gruvbox's dark colors")
    colors = dict(re.findall(r"(\w+) = p\.(\w+)", dark.group(1)))
    groups = dict(re.findall(r"(Gruvbox\w+) = \{ fg = colors\.(\w+)", source))
    result = {}
    for group, link in re.findall(
            r'(MiniIcons\w+) = \{ link = "(\w+)" \}', source):
      color = colors.get(groups.get(link))
      if color in palette:
        result[group] = palette[color]
    if not result:
      fail("couldn't parse gruvbox's colors for mini.icons")
    return result

  def resolve(self, entry):
    if isinstance(entry, str):
      entry = self.filetype.get(entry)
    if entry is None:
      return None
    glyph, group = entry
    return glyph, self.colors.get(group, "")

  def get_extension(self, ext):
    if ext in self.extension:
      return self.resolve(self.extension[ext])
    # Parts of a complex extension, e.g. gz for tar.gz.
    part = ext
    while "." in part[1:]:
      part = part.split(".", 1)[1]
      if part in self.extension:
        return self.resolve(self.extension[part])
    filetype = self.ft_extension.get(ext.rsplit(".", 1)[-1])
    return self.resolve(filetype) if filetype else None

  def get(self, kind, name):
    if kind == "dir":
      return self.resolve(self.directory.get(name))
    if kind == "ext":
      return self.get_extension(name)
    if name in self.file:
      return self.resolve(self.file[name])
    dot = name.find(".", 1)
    if 0 < dot < len(name) - 1:
      found = self.get_extension(name[dot + 1:].lower())
      if found:
        return found
    filetype = self.ft_filename.get(name)
    return self.resolve(filetype) if filetype else None


class Eza:
  """eza's icons (and their colors, from LS_COLORS and eza's theme), from
  running eza on a sample file or directory for each entry."""

  def __init__(self, refresh):
    # eza's own icon table, and its default icons (used when a name isn't
    # in it), from its source for the installed version.
    source = fetch("eza-icons.rs", refresh)
    consts = {name: chr(int(code, 16)) for name, code in re.findall(
        r"const (\w+)\s*:\s*char\s*=\s*'\\u\{([0-9a-fA-F]+)\}'", source)}
    self.defaults = {consts[name] for name in
                     ("FILE", "FILE_UNKNOW", "FOLDER", "FOLDER_OPEN")}
    # Which of them are used for which of DEFAULTS.
    self.builtin_defaults = {"file": consts["FILE"],
                             "noext": consts["FILE_UNKNOW"],
                             "dir": consts["FOLDER"]}
    self.table = {}
    for table, kind in (("DIRECTORY_ICONS", "dir"),
                        ("FILENAME_ICONS", "file"),
                        ("EXTENSION_ICONS", "ext")):
      body = source[source.index(table + ":"):]
      body = body[body.index("{") + 1:body.index("};")]
      entries = re.findall(r'"([^"]+)"\s*=>\s*(?:Icons::(\w+)|'
                           r"'\\u\{([0-9a-fA-F]+)\}')", body)
      if len(entries) != body.count("=>"):
        fail(f"couldn't parse every entry in eza's {table}")
      for key, const, code in entries:
        self.table[(kind, key)] = (
            consts[const] if const else chr(int(code, 16)))

  def run(self, entries):
    """Return {(kind, name): (glyph or None, SGR)} for the given entries,
    where the glyph is None if it's one of eza's defaults."""
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
      # Each entry gets its own directory, so names differing only in
      # case don't clash on case-insensitive file systems (e.g. macOS).
      dirs = []
      for i, (kind, name) in enumerate(entries):
        parent = pathlib.Path(tmp, str(i))
        parent.mkdir()
        if kind == "dir":
          (parent / name).mkdir()
          (parent / name / "f").touch()
        else:
          (parent / (name if kind == "file" else "x." + name)).touch()
        dirs.append(str(parent))
      out = subprocess.run(
          ["eza", "-1a", "--icons=always", "--color=always", *dirs],
          capture_output=True, text=True, check=True,
          stdin=subprocess.DEVNULL).stdout
    index = None
    for line in out.splitlines():
      plain = re.sub(r"\x1b\[[0-9;]*m", "", line)
      header = re.fullmatch(r".*/(\d+):", plain)
      if header:
        index = int(header.group(1))
        continue
      match = re.match(r"(?:\x1b\[([0-9;]*)m)?(\S) ", line)
      if match and index is not None:
        glyph = match.group(2)
        results[entries[index]] = (
            None if glyph in self.defaults else glyph, match.group(1) or "")
    return results


def read_icons(glyphs):
  """Read data/icons.txt: returns (palette, entries, defaults), where entries
  are (kind, name, icon, color) in file order, with kind one of KINDS or
  "filetype", and defaults are {kind: (icon, color)} for DEFAULTS."""
  if not ICONS.exists():
    fail(f"{ICONS} doesn't exist (see `icons.py seed`)")
  palette, entries, defaults, errors = {}, [], {}, []
  for number, line in enumerate(ICONS.read_text(encoding="utf-8").splitlines(),
                                1):
    fields = line.split()
    if not fields or line.startswith("#"):
      continue
    if fields[0] == "color" and len(fields) == 3:
      palette[fields[1]] = fields[2]
    elif fields[0] == "default" and len(fields) == 4 and fields[1] in DEFAULTS:
      defaults[fields[1]] = (number, *fields[2:])
    elif fields[0] in (*KINDS, "filetype") and len(fields) == 4:
      entries.append((number, *fields))
    else:
      errors.append(f"line {number}: expected 'color NAME HEX', "
                    "'default KIND ICON COLOR' or 'KIND NAME ICON COLOR'")
  checks = [(number, icon, color) for number, _, _, icon, color in entries]
  checks += list(defaults.values())
  for number, icon, color in checks:
    if glyphs.glyph(icon) is None:
      errors.append(f"line {number}: unknown icon {icon}")
    if color not in palette:
      errors.append(f"line {number}: unknown color {color}")
  missing = [kind for kind in DEFAULTS if kind not in defaults]
  if missing:
    errors.append("no default for: " + ", ".join(missing))
  if errors:
    fail("errors in data/icons.txt:\n  " + "\n  ".join(errors))
  return (palette, [entry[1:] for entry in entries],
          {kind: value[1:] for kind, value in defaults.items()})


def truecolor(hex_color):
  if not hex_color:
    return ""
  r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
  return f"\x1b[38;2;{r};{g};{b}m"


def cell(color, glyph):
  """An icon in a color (or - if there isn't one), followed by spaces; kitty
  only draws an icon wider than a cell if it's followed by a space."""
  return f"{color}{glyph}\x1b[0m     " if glyph else "-     "


def compare(refresh):
  glyphs = Glyphs(refresh)
  palette, entries, _ = read_icons(glyphs)
  entries = [entry for entry in entries if entry[0] in KINDS]
  devicons, mini, eza = Devicons(refresh), MiniIcons(refresh), Eza(refresh)
  eza_results = eza.run([(kind, name) for kind, name, _, _ in entries])

  for kind in KINDS:
    rows = [entry for entry in entries if entry[0] == kind]
    if not rows:
      continue
    print(f"\n\x1b[1m{TITLES[kind] + f' ({len(rows)})':<36} "
          f"{'dev':<6}{'mini':<6}{'eza':<6}{'ours':<6}ours-eza\x1b[0m")
    for _, name, icon, color in rows:
      label = {"dir": name + "/", "file": name, "ext": "*." + name}[kind]
      dev = devicons.get(kind, name)
      min_ = mini.get(kind, name)
      eza_glyph, eza_sgr = eza_results.get((kind, name), (None, ""))
      eza_color = f"\x1b[{eza_sgr}m" if eza_sgr else ""
      ours = glyphs.glyph(icon)
      print(f"  {label:<34} "
            + cell(truecolor(dev[1]) if dev else "", dev and dev[0])
            + cell(truecolor(min_[1]) if min_ else "", min_ and min_[0])
            + cell(eza_color, eza_glyph)
            + cell(truecolor(palette[color]), ours)
            + cell(eza_color, ours))


def seed(force, refresh):
  if ICONS.exists() and not force:
    fail(f"{ICONS} already exists (use --force to replace it)")
  glyphs = Glyphs(refresh)
  devicons, mini, eza = Devicons(refresh), MiniIcons(refresh), Eza(refresh)

  # Every name any of them has an icon for, by kind: all of eza's (whose
  # file names are case sensitive, e.g. Justfile and justfile), then those of
  # mini.icons and devicons (which lowercases file names) that aren't just
  # eza's in another case.
  names = {kind: {} for kind in KINDS}
  for kind, name in eza.table:
    names[kind][name] = name
  for kind, table in (("dir", mini.directory), ("file", mini.file),
                      ("ext", mini.extension), ("file", devicons.filename),
                      ("ext", devicons.extension)):
    seen = {name.lower() for name in names[kind]}
    for name in table:
      if name.lower() not in seen:
        names[kind][name] = name
        seen.add(name.lower())

  def nearest(hex_color):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return min(SEED_PALETTE, key=lambda c: sum(
        (x - int(SEED_PALETTE[c][i:i + 2], 16)) ** 2
        for x, i in zip((r, g, b), (1, 3, 5))))

  def seed_color(kind, name, found):
    if kind == "dir":
      return "dark-blue"
    lower = name.lower()
    ext = lower if kind == "ext" else lower.rsplit(".", 1)[-1] \
        if "." in lower[1:] else None
    for color, rules in SEED_COLORS.items():
      if lower in rules["names"] or ext in rules["extensions"]:
        return color
    return nearest(found) if found else "plain"

  lines = []
  for kind in KINDS:
    for name in sorted(names[kind].values(), key=str.lower):
      dev, min_ = devicons.get(kind, name), mini.get(kind, name)
      glyph = eza.table.get((kind, name)) \
          or (min_ and min_[0]) or (dev and dev[0])
      if not glyph:
        continue
      color = seed_color(kind, name, (dev and dev[1]) or (min_ and min_[1]))
      lines.append((kind, name, glyphs.name(glyph), color))

  width = [max(len(line[i]) for line in lines) for i in range(3)]
  text = [
      ("# Icons, and their colors, for directories, file names and extensions:"
       " the"),
      "# source of truth for our eza and nvim icons. See icons.py.",
      "#",
      ("# \"color NAME HEX\" lines define the colors. The others are \"KIND"
       " NAME ICON"),
      ("# COLOR\", where KIND is dir, file or ext, ICON is a Nerd Font glyph"
       " name"),
      "# (e.g. oct-gear) or codepoint (e.g. U+F423), and COLOR is one of the",
      "# colors. Names can't contain whitespace, and lines starting with # are",
      "# comments.",
      "",
      "# gruvbox's (dark) palette.",
      *(f"color {name:<12} {hex_}" for name, hex_ in SEED_PALETTE.items()),
  ]
  for kind in KINDS:
    text += ["", f"# {TITLES[kind]}."]
    text += [f"{k:<4} {n:<{width[1]}} {i:<{width[2]}} {c}"
             for k, n, i, c in lines if k == kind]
  ICONS.parent.mkdir(parents=True, exist_ok=True)
  ICONS.write_text("\n".join(text) + "\n", encoding="utf-8")
  counts = {kind: sum(1 for line in lines if line[0] == kind) for kind in KINDS}
  print(f"Wrote {ICONS}: {counts['dir']} directories, {counts['file']} file "
        f"names, {counts['ext']} extensions.")


def main():
  args = sys.argv[1:]
  refresh = "--refresh" in args
  if args[:1] == ["compare"]:
    compare(refresh)
  elif args[:1] == ["seed"]:
    seed("--force" in args, refresh)
  else:
    sys.exit(__doc__)


if __name__ == "__main__":
  main()
