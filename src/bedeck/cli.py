"""Command line interface for bedeck."""

import typer


app = typer.Typer(add_completion=True)


@app.callback()
def main() -> None:
  """Tool for generating consistent CLI themes."""
