"""Self-contained HTML: bars are plain HTML boxes sized from the numbers (no images, no SVG)."""

import html
from typing import List

from . import sections, texts
from .stats import Row, Summary

STYLE = """
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#222;max-width:860px;margin:2rem auto;padding:0 1rem;line-height:1.45}
h1{font-size:1.6rem;margin:0 0 .3rem}h2{font-size:1.2rem;margin:2.4rem 0 .3rem}
.lead,.intro,.note{color:#666}.intro{margin:0 0 1rem}.note{font-size:.85rem}
dl{display:grid;grid-template-columns:14rem 1fr;gap:.25rem 1rem}dt{color:#666}dd{margin:0}
dl.def dt{color:#222;font-weight:600}
table{border-collapse:collapse;width:100%;font-size:.9rem}
th,td{padding:.25rem .5rem;border-bottom:1px solid #e3e3e3;text-align:right}
th:first-child,td:first-child{text-align:left}th{background:#f4f4f4}
.chart{display:grid;grid-template-columns:15rem 1fr 11rem;gap:.35rem .6rem;align-items:center;font-size:.9rem}
.track{position:relative;height:1.1rem;background:#f1f3f6}
.bar{position:absolute;left:0;top:0;bottom:0;background:#3b6ea8}
.range{position:absolute;top:45%;height:2px;background:#222}
.value{color:#666;font-size:.85rem}
"""


def _e(text) -> str:
    return html.escape(str(text))


def _chart(rows: List[Row], value, label, ranges: bool = False) -> str:
    top = max([r.high if ranges else value(r) for r in rows] + [1e-9])
    out = ['<div class="chart">']
    for r in rows:
        width = value(r) / top * 100
        extra = ""
        if ranges:
            extra = (f'<div class="range" style="left:{r.low / top * 100:.2f}%;'
                     f'width:{(r.high - r.low) / top * 100:.2f}%"></div>')
        out.append(f'<div>{_e(r.label)}</div><div class="track"><div class="bar" style="width:{width:.2f}%">'
                   f'</div>{extra}</div><div class="value">{_e(label(r))}</div>')
    out.append("</div>")
    return "\n".join(out)


def _table(header: List[str], body: List[List[str]]) -> str:
    head = "".join(f"<th>{_e(h)}</th>" for h in header)
    rows = "".join("<tr>" + "".join(f"<td>{_e(c)}</td>" for c in row) + "</tr>" for row in body)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"


def render(s: Summary, min_games: int, top: int) -> str:
    parts = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
             f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
             f"<title>{_e(texts.title(s))}</title><style>{STYLE}</style></head><body>",
             f"<h1>{_e(texts.title(s))}</h1><p class='lead'>{_e(texts.SUBTITLE)}</p>",
             "<h2>Data</h2><dl>" + "".join(f"<dt>{_e(a)}</dt><dd>{_e(b)}</dd>" for a, b in texts.data_lines(s)) + "</dl>",
             "<h2>Definitions</h2><dl class='def'>" +
             "".join(f"<dt>{_e(a)}</dt><dd>{_e(b)}</dd>" for a, b in texts.definitions(min_games)) + "</dl>"]

    def head(key):
        title, intro = texts.SECTIONS[key]
        return f"<h2>{_e(title)}</h2><p class='intro'>{_e(intro.format(min_games=min_games))}</p>"

    parts.append(head("common_type") + _chart(
        sections.common_types(s), lambda r: r.per_100_games,
        lambda r: f"{r.per_100_games:.1f}  (n={r.games:,})"))
    parts.append(head("common_material") + _table(
        ["Material", "Games", "In N of 100 games", "Moves played"],
        [[r.label, f"{r.games:,}", f"{r.per_100_games:.2f}", f"{r.moves:,}"] for r in sections.common_materials(s, top)]))
    parts.append(head("tricky_type") + _chart(
        sections.tricky_types(s, min_games), lambda r: r.blunders_per_100,
        lambda r: f"{r.blunders_per_100:.0f}  ({r.blunders:,} in {r.games:,} games)", ranges=True))
    parts.append(head("tricky_material") + _table(
        ["Material", "Games", "Blunders", "Per 100 games (95% range)", "Per 1000 moves"],
        [[r.label, f"{r.games:,}", f"{r.blunders:,}", f"{r.blunders_per_100:.0f} ({r.low:.0f}-{r.high:.0f})",
          f"{r.blunders_per_1000_moves:.1f}"] for r in sections.tricky_materials(s, min_games, top)]) +
        f"<p class='note'>{sections.unranked_materials(s, min_games)} other materials were reached in fewer than "
        f"{min_games} games and are not ranked.</p>")
    parts.append("</body></html>")
    return "\n".join(parts)
