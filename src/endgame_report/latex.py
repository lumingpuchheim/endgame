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
\definecolor{muted}{HTML}{666666}
\setlength{\parindent}{0pt}
\setlength{\parskip}{4pt}
\begin{document}
"""

LEFT = r">{\raggedright\arraybackslash}"


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
           head("common") + _table(
               ["Material", "Games", "In N of 100 games"],
               [[r.label, f"{r.games:,}", f"{r.per_100_games:.2f}"] for r in sections.most_common(s, top)], "lrr"),
           head("tricky") + _table(
               ["Material", "Games", "Blunders", "Per 100 games (95% range)"],
               [[r.label, f"{r.games:,}", f"{r.blunders:,}", f"{r.blunders_per_100:.0f} ({r.low:.0f}-{r.high:.0f})"]
                for r in sections.trickiest(s, min_games, top)], "lrrr") +
           f"\n\\vspace{{6pt}}{{\\footnotesize\\color{{muted}}{sections.unranked(s, min_games)} other materials "
           f"were reached in fewer than {min_games} games and are not ranked.\\par}}\n",
           "\\end{document}\n"]
    return "\n".join(out)
