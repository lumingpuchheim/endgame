"""LaTeX source for the report; compiled to PDF by build.py."""

from typing import List

from . import sections, texts
from .stats import Summary

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

LEFT = r">{\raggedright\arraybackslash}"


def _chart(rows, value, label) -> str:
    """Horizontal bars drawn by pgfplots from the numbers written here."""
    rows = rows[::-1]                     # pgfplots draws bottom-up; keep the first row on top
    names = ",".join("{" + esc(r.label) + "}" for r in rows)
    coords = " ".join(f"({value(r):.3f},{i})" for i, r in enumerate(rows))
    side = "\n".join(f"\\node[anchor=west,font=\\footnotesize,text=muted] at "
                     f"(axis description cs:1.02,{(i + 0.5) / len(rows):.4f}) {{{esc(label(r))}}};"
                     for i, r in enumerate(rows))
    height = max(5.0, min(23.0, 0.8 * len(rows) + 1.5))
    return (f"\\begin{{tikzpicture}}\n\\begin{{axis}}[xbar,width=8cm,height={height:.1f}cm,xmin=0,"
            f"ytick={{0,...,{len(rows) - 1}}},yticklabels={{{names}}},"
            f"ymin=-0.5,ymax={len(rows) - 0.5},enlarge y limits=false,bar width=7pt,"
            f"xmajorgrids,grid style={{gray!20}},axis x line*=bottom,axis y line*=left,"
            f"tick label style={{font=\\small}},clip=false]\n"
            f"\\addplot[fill=bar,draw=none] coordinates {{{coords}}};\n"
            f"{side}\n\\end{{axis}}\n\\end{{tikzpicture}}\n")


def _table(header: List[str], body: List[List[str]], align: str) -> str:
    lines = [f"\\begin{{tabular}}{{{align}}}", "\\toprule",
             " & ".join(f"\\textbf{{{esc(h)}}}" for h in header) + r" \\", "\\midrule"]
    lines += [" & ".join(esc(c) for c in row) + r" \\" for row in body]
    lines += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(lines) + "\n"


def render(s: Summary, min_games: int, top: int) -> str:
    def head(key):
        title, intro = texts.SECTIONS[key]
        return (f"\\newpage\n\\section*{{{esc(title)}}}\n"
                f"{{\\color{{muted}}{esc(intro.format(min_games=min_games))}\\par}}\n\\vspace{{8pt}}\n")

    out = [PREAMBLE,
           f"{{\\LARGE\\bfseries {esc(texts.title(s))}\\par}}\n\\vspace{{2pt}}\n{{\\color{{muted}}{esc(texts.SUBTITLE)}\\par}}\n",
           f"\\section*{{Data}}\n\\begin{{tabular}}{{@{{}}{LEFT}p{{5cm}}{LEFT}p{{11cm}}@{{}}}}\n" +
           "\n".join(f"\\textcolor{{muted}}{{{esc(a)}}} & {esc(b)} \\\\" for a, b in texts.data_lines(s)) +
           "\n\\end{tabular}\n",
           f"\\section*{{Definitions}}\n\\begin{{tabular}}{{@{{}}{LEFT}p{{3.6cm}}{LEFT}p{{12.4cm}}@{{}}}}\n" +
           "\n".join(f"\\textbf{{{esc(a)}}} & {esc(b)} \\\\[3pt]" for a, b in texts.definitions(min_games)) +
           "\n\\end{tabular}\n",
           head("common") + _chart(sections.most_common(s, top), lambda r: r.per_100_games,
                                   lambda r: f"{r.per_100_games:.1f} of 100  ({r.games:,} games)"),
           head("tricky") + _chart(sections.trickiest(s, min_games, top), lambda r: r.blunders_per_100,
                                   lambda r: f"{r.blunders_per_100:.0f}  ({r.blunders:,} in {r.games:,} games)") +
           f"\n\\vspace{{6pt}}{{\\footnotesize\\color{{muted}}{sections.unranked(s, min_games)} other materials "
           f"were reached in fewer than {min_games} games and are not ranked.\\par}}\n",
           "\\end{document}\n"]
    return "\n".join(out)
