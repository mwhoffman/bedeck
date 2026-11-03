"""Preview a theme, by printing mock-ups of what it's used for in its colors."""

import pathlib

import jinja2
import rich.console
import rich.padding
import rich.text

import bedeck.errors
import bedeck.theme


# The preview: a template of rich's markup.
PREVIEW = pathlib.Path(__file__).parent / "data/preview.jinja"


def show(theme: pathlib.Path) -> None:
  """Print the preview of a theme, on the theme's background."""
  colors, roles = bedeck.theme.load(theme)
  env = jinja2.Environment(
    trim_blocks=True, lstrip_blocks=True, undefined=jinja2.StrictUndefined
  )
  template = env.from_string(PREVIEW.read_text(encoding="utf-8"))
  context = {"colors": colors, "ansi": bedeck.theme.ANSI}
  try:
    markup = template.render(context | roles)
    ui = roles["ui"]
    style = f"{ui['text']} on {ui['background']}"
  except (jinja2.UndefinedError, KeyError) as error:
    raise bedeck.errors.BedeckError(
      f"{theme}: the preview needs a color or role it doesn't have: {error}"
    ) from error
  text = rich.text.Text.from_markup(markup, emoji=False)
  console = rich.console.Console(highlight=False)
  console.print(rich.padding.Padding(text, (1, 2), style=style, expand=False))
