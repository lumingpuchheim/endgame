"""LaTeX source: charts are pgfplots commands with the numbers written in, so LaTeX draws them."""

from typing import List

from . import sections, texts
from .stats import Row, Summary

_SPECIAL = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
            "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def esc(text) -> str:
    return "".join(_SPECIAL.get(ch, ch) for ch in str(text))


PREAMBLE = r"""\documentclass[a4paper,11pt]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage[margin=2cm]{geometry}
\usepackage{booktabs}
\usepackage{array}
\usepackage{xcolor}
\usepackage{pgfplots}
\pgfplotsset{compat=1.16}
\definecolor{bar}{HTML}{3B6EA8}
\definecolor{muted}{HTML}{666666}
\setlength{\parindent}{0pt}
\setlength{\parskip}{4pt}
\begin{document}
"""


def _chart(rows: List[Row], value, label, ranges: bool = False) -> str:
    rows = rows[::-1]                     # pgfplots draws bottom-up; keep the top row on top
    names = ",".join("{" + esc(r.label) + "}" for r in rows)
    coords = []
    for i, r in enumerate(rows):
        v = value(r)
        if ranges:
            coords.append(f"({v:.3f},{i}) += ({r.high - v:.3f},0) -= ({v - r.low:.3f},0)")
        else:
            coords.append(f"({v:.3f},{i})")
    side = "\n".join(f"\\node[anchor=west,font=\\footnotesize,text=muted] at (axis description cs:1.02,{(i + 0.5) / len(rows):.4f}) {{{esc(label(r))}}};"
                     for i, r in enumerate(rows))
    errors = ",error bars/.cd,x dir=both,x explicit" if ranges else ""
    height = max(5.0, 1.0 * len(rows) + 1.5)
    return (f"\\begin{{tikzpicture}}\n\\begin{{axis}}[xbar,width=9cm,height={height:.1f}cm,xmin=0,"
            f"ytick={{0,...,{len(rows) - 1}}},yticklabels={{{names}}},y tick label style={{font=\\small}},"
            f"ymin=-0.5,ymax={len(rows) - 0.5},enlarge y limits=false,bar width=9pt,"
            f"xmajorgrids,grid style={{gray!20}},axis x line*=bottom,axis y line*=left,"
            f"tick label style={{font=\\small}},clip=false]\n"
            f"\\addplot[fill=bar,draw=none{errors}] coordinates {{{' '.join(coords)}}};\n"
            f"{side}\n\\end{{axis}}\n\\end{{tikzpicture}}\n")


def _table(header: List[str], body: List[List[str]], align: str) -> str:
    lines = [f"\\begin{{tabular}}{{{align}}}", "\\toprule",
             " & ".join(f"\\textbf{{{esc(h)}}}" for h in header) + r" \\", "\\midrule"]
    lines += [" & ".join(esc(c) for c in row) + r" \\" for row in body]
    lines += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(lines) + "\n"


def render(s: Summary, min_games: int, top: int) -> str:
    out = [PREAMBLE,
           f"{{\\LARGE\\bfseries {esc(texts.title(s))}\\par}}\n\\vspace{{2pt}}\n{{\\color{{muted}}{esc(texts.SUBTITLE)}\\par}}\n",
           "\\section*{Data}\n\\begin{tabular}{@{}>{\\raggedright\\arraybackslash}p{5cm}>{\\raggedright\\arraybackslash}p{11cm}@{}}\n" +
           "\n".join(f"\\textcolor{{muted}}{{{esc(a)}}} & {esc(b)} \\\\" for a, b in texts.data_lines(s)) +
           "\n\\end{tabular}\n",
           "\\section*{Definitions}\n\\begin{tabular}{@{}>{\\raggedright\\arraybackslash}p{3.6cm}>{\\raggedright\\arraybackslash}p{12.4cm}@{}}\n" +
           "\n".join(f"\\textbf{{{esc(a)}}} & {esc(b)} \\\\[3pt]" for a, b in texts.definitions(min_games)) +
           "\n\\end{tabular}\n"]

    def head(key):
        title, intro = texts.SECTIONS[key]
        return (f"\\newpage\n\\section*{{{esc(title)}}}\n"
                f"{{\\color{{muted}}{esc(intro.format(min_games=min_games))}\\par}}\n\\vspace{{8pt}}\n")

    out.append(head("common_type") + _chart(
        sections.common_types(s), lambda r: r.per_100_games,
        lambda r: f"{r.per_100_games:.1f}  (n={r.games:,})"))
    out.append(head("common_material") + _table(
        ["Material", "Games", "In N of 100 games", "Moves played"],
        [[r.label, f"{r.games:,}", f"{r.per_100_games:.2f}", f"{r.moves:,}"] for r in sections.common_materials(s, top)],
        "lrrr"))
    out.append(head("tricky_type") + _chart(
        sections.tricky_types(s, min_games), lambda r: r.blunders_per_100,
        lambda r: f"{r.blunders_per_100:.0f}  ({r.blunders:,} in {r.games:,} games)", ranges=True))
    out.append(head("tricky_material") + _table(
        ["Material", "Games", "Blunders", "Per 100 games (95% range)", "Per 1000 moves"],
        [[r.label, f"{r.games:,}", f"{r.blunders:,}", f"{r.blunders_per_100:.0f} ({r.low:.0f}-{r.high:.0f})",
          f"{r.blunders_per_1000_moves:.1f}"] for r in sections.tricky_materials(s, min_games, top)],
        "lrrrr") +
        f"\n\\vspace{{6pt}}{{\\footnotesize\\color{{muted}}{sections.unranked_materials(s, min_games)} other "
        f"materials were reached in fewer than {min_games} games and are not ranked.\\par}}\n")
    out.append("\\end{document}\n")
    return "\n".join(out)
