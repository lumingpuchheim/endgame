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
table{border-collapse:collapse;width:100%;font-size:.9rem}
th,td{padding:.25rem .5rem;border-bottom:1px solid #e3e3e3;text-align:right}
th:first-child,td:first-child{text-align:left}th{background:#f4f4f4}
"""


def _e(text) -> str:
    return html.escape(str(text))


def _table(header: List[str], body: List[List[str]]) -> str:
    head = "".join(f"<th>{_e(h)}</th>" for h in header)
    rows = "".join("<tr>" + "".join(f"<td>{_e(c)}</td>" for c in row) + "</tr>" for row in body)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"


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
        head("common") + _table(
            ["Material", "Games", "In N of 100 games"],
            [[r.label, f"{r.games:,}", f"{r.per_100_games:.2f}"] for r in sections.most_common(s, top)]),
        head("tricky") + _table(
            ["Material", "Games", "Blunders", "Per 100 games (95% range)"],
            [[r.label, f"{r.games:,}", f"{r.blunders:,}", f"{r.blunders_per_100:.0f} ({r.low:.0f}-{r.high:.0f})"]
             for r in sections.trickiest(s, min_games, top)]) +
        f"<p class='note'>{sections.unranked(s, min_games)} other materials were reached in fewer than "
        f"{min_games} games and are not ranked.</p>",
        "</body></html>",
    ]
    return "\n".join(parts)
