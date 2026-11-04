"""
theme.py - Shared look and feel for the whole app
=================================================
Owns: loading the stylesheets, icons and images, and restyling the Plotly
charts drawn by the modules.

The colours, type and component rules live in assets/theme/theme.css (every
page) and assets/theme/home.css (home page only). Change them there.
"""

import base64
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
THEME_DIR = ROOT / "assets" / "theme"
ICON_DIR = ROOT / "assets" / "icons" / "line"
IMAGE_DIR = ROOT / "assets" / "images"

INK = "#111826"

# The modules draw charts with dark-theme colours. These are the light swaps.
CHART_COLOURS = {
    "#00e5ff": INK,        # gauge needle bar
    "#5c1020": "#F9D6DA",  # gauge: low
    "#5c4a10": "#FFEFC7",  # gauge: middle
    "#0b3a24": "#CDEFE6",  # gauge: high
    "#00e676": "#00838C",  # bar: strong
    "#ffc400": "#FFC030",  # bar: middle
    "#ff1744": "#DD0822",  # bar: weak
}


def stylesheet(name):
    """Return a CSS file from assets/theme wrapped in a <style> tag."""
    return f"<style>{(THEME_DIR / name).read_text(encoding='utf-8')}</style>"


def icon(name, size=40, colour=INK):
    """Return a line icon from assets/icons/line as an <img>.
    st.html removes inline <svg>, so the colour is written into the file data."""
    svg = (ICON_DIR / f"{name}.svg").read_text(encoding="utf-8")
    svg = svg.replace("currentColor", colour).replace('stroke-width="2"', 'stroke-width="1.5"')
    data = base64.b64encode(svg.encode()).decode()
    return (f"<img class='ui-icon' src='data:image/svg+xml;base64,{data}' "
            f"width='{size}' height='{size}' alt=''>")


def image_uri(filename):
    """Return an image from assets/images as a data URI, or "" if it is missing."""
    path = IMAGE_DIR / filename
    if not path.exists():
        return ""
    mime = "image/svg+xml" if path.suffix == ".svg" else "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def page_html(markup):
    """Draw static HTML. Lines are joined so templates can be indented."""
    st.html(" ".join(line.strip() for line in markup.splitlines()))


def _swap(colour):
    return CHART_COLOURS.get(str(colour).lower(), colour)


def style_figure(fig):
    """Move a module's dark Plotly chart onto the light theme, in place."""
    font = {"family": "DM Sans, sans-serif", "color": INK}
    fig.update_layout(
        template="plotly_white",
        font=font,
        title_font=font,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    for trace in fig.data:
        if trace.type == "indicator" and trace.gauge is not None:
            trace.title.font = {**font, "size": 21}
            trace.number.font = font
            trace.gauge.bar.color = _swap(trace.gauge.bar.color)
            trace.gauge.steps = [
                {"range": step.range, "color": _swap(step.color)}
                for step in trace.gauge.steps
            ]
            fig.update_layout(margin_b=24)  # room for the 0 and 100 labels
        elif trace.type == "bar" and trace.marker.color is not None:
            colours = trace.marker.color
            trace.marker.color = (
                [_swap(c) for c in colours]
                if isinstance(colours, (list, tuple))
                else _swap(colours)
            )
    return fig
