"""Self-contained HTML page (no images, no scripts)."""

import html
from typing import List

from . import sections, texts
from .stats import Summary

STYLE = """
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#222;max-width:860px;margin:2rem auto;padding:0 1rem;line-height:1.45}
h1{font-size:1.6rem;margin:0 0 .3rem}h2{font-size:1.2rem;margin:2.4rem 0 .3rem}
.lead,.intro,.note{color:#666}.intro{margin:0 0 1rem}.note{font-size:.85rem}
dl{display:grid;grid-template-columns:14rem 1fr;gap:.25rem 1rem}dt{color:#666}dd{margin:0}
dl.def dt{color:#222;font-weight:600}
.chart{display:grid;grid-template-columns:8rem 1fr 13rem;gap:.3rem .6rem;align-items:center;font-size:.9rem}
.track{height:1rem;background:#f1f3f6}.bar{height:100%;background:#3b6ea8}
.value{color:#555;font-size:.85rem}
"""


def _e(text) -> str:
    return html.escape(str(text))


def _chart(rows, value, label) -> str:
    """One bar per row; the bar width is the value relative to the largest value."""
    top = max([value(r) for r in rows] + [1e-9])
    cells = [f"<div>{_e(r.label)}</div><div class='track'><div class='bar' style='width:{value(r) / top * 100:.2f}%'>"
             f"</div></div><div class='value'>{_e(label(r))}</div>" for r in rows]
    return "<div class='chart'>" + "".join(cells) + "</div>"


def render(s: Summary, min_games: int, top: int) -> str:
    def head(key):
        title, intro = texts.SECTIONS[key]
        return f"<h2>{_e(title)}</h2><p class='intro'>{_e(intro.format(min_games=min_games))}</p>"

    parts = [
        f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{_e(texts.title(s))}</title><style>{STYLE}</style></head><body>",
        f"<h1>{_e(texts.title(s))}</h1><p class='lead'>{_e(texts.SUBTITLE)}</p>",
        "<h2>Data</h2><dl>" + "".join(f"<dt>{_e(a)}</dt><dd>{_e(b)}</dd>" for a, b in texts.data_lines(s)) + "</dl>",
        "<h2>Definitions</h2><dl class='def'>" +
        "".join(f"<dt>{_e(a)}</dt><dd>{_e(b)}</dd>" for a, b in texts.definitions(min_games)) + "</dl>",
        head("common") + _chart(sections.most_common(s, top), lambda r: r.per_100_games,
                                lambda r: f"{r.per_100_games:.1f} of 100  ({r.games:,} games)"),
        head("tricky") + _chart(sections.trickiest(s, min_games, top), lambda r: r.blunders_per_100,
                                lambda r: f"{r.blunders_per_100:.0f}  ({r.blunders:,} in {r.games:,} games)") +
        f"<p class='note'>{sections.unranked(s, min_games)} other materials were reached in fewer than "
        f"{min_games} games and are not ranked.</p>",
        "</body></html>",
    ]
    return "\n".join(parts)
