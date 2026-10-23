"""LaTeX source for the report; compiled to PDF by build.py."""

from typing import List, Optional
from urllib.parse import quote

from . import sections, texts
from .game_line import Diagram, figurine
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
\usepackage{chessboard}
\PassOptionsToPackage{obeyspaces}{url}
\usepackage[hidelinks]{hyperref}
\pgfplotsset{compat=1.16}
\definecolor{bar}{HTML}{3B6EA8}
\definecolor{muted}{HTML}{666666}
\setlength{\parindent}{0pt}
\setlength{\parskip}{4pt}
% Chess figures in moves: \K e2, \R xc1+, e8=\Q
\newcommand{\K}{\symking}
\newcommand{\Q}{\symqueen}
\newcommand{\R}{\symrook}
\newcommand{\B}{\symbishop}
\newcommand{\N}{\symknight}
% \game{White (Elo)}{Black (Elo)}{Event}
\newcommand{\game}[3]{\par\vspace{14pt}\noindent\textbf{#1 -- #2}\\{\color{muted}#3}\par\nopagebreak}
% \diagram[label]{FEN}: number, Lichess link, board
\newcounter{diagram}
\makeatletter
\def\eg@url#1 #2 #3 #4 #5 #6\@nil{https://lichess.org/analysis/standard/#1_#2_#3_#4_#5_#6}
\newcommand{\diagram}[2][]{\refstepcounter{diagram}\if\relax\detokenize{#1}\relax\else\label{#1}\fi
  \par\vspace{6pt}\noindent\textbf{Diagram \thediagram}\par\nopagebreak
  \noindent\edef\eg@link{\eg@url#2\@nil}%
  \expandafter\href\expandafter{\eg@link}{\textcolor{bar}{Open on Lichess}}\par\nopagebreak
  \noindent\chessboard[setfen=#2,showmover=true,boardfontsize=17pt,labelfontsize=7pt]\par\vspace{6pt}}
\makeatother
% \moves{61.\R b7? \K e6}: the moves of the game
\newcommand{\moves}[1]{\textbf{#1}}
% \seen{label}: the game reaches a position shown before
\newcommand{\seen}[1]{We have already seen this position in diagram~\ref{#1}.\par}
\begin{document}
"""

LEFT = r">{\raggedright\arraybackslash}"


OVERALL_TOP = 15


def _chart(rows, value, label, width: str = "8cm") -> str:
    """Horizontal bars drawn by pgfplots from the numbers written here."""
    rows = rows[::-1]                     # pgfplots draws bottom-up; keep the first row on top
    names = ",".join("{" + esc(r.label) + "}" for r in rows)
    coords = " ".join(f"({value(r):.3f},{i})" for i, r in enumerate(rows))
    side = "\n".join(f"\\node[anchor=west,font=\\footnotesize,text=muted] at "
                     f"(axis description cs:1.02,{(i + 0.5) / len(rows):.4f}) {{{esc(label(r))}}};"
                     for i, r in enumerate(rows))
    height = max(5.0, min(23.0, 0.8 * len(rows) + 1.5))
    return (f"\\begin{{tikzpicture}}\n\\begin{{axis}}[xbar,width={width},height={height:.1f}cm,xmin=0,"
            f"ytick={{0,...,{len(rows) - 1}}},yticklabels={{{names}}},"
            f"ymin=-0.5,ymax={len(rows) - 0.5},enlarge y limits=false,bar width=7pt,"
            f"xmajorgrids,grid style={{gray!20}},axis x line*=bottom,axis y line*=left,"
            f"tick label style={{font=\\small}},clip=false]\n"
            f"\\addplot[fill=bar,draw=none] coordinates {{{coords}}};\n"
            f"{side}\n\\end{{axis}}\n\\end{{tikzpicture}}\n")


def _standing(side: str, group: str) -> str:
    """'White winning', 'equal' or 'White losing'."""
    return "equal" if group == "equal" else f"{side} {group}"


def lichess_url(fen: str) -> str:
    """Lichess analysis board for a FEN (spaces become underscores)."""
    return "https://lichess.org/analysis/standard/" + quote(fen.replace(" ", "_"), safe="/_-")


def _move(number: str, mover: str, san: str) -> str:
    return f"{number}. {san}" if mover == "white" else f"{number}... {san}"


def _diagram(d: Diagram) -> str:
    return f"\\diagram[{d.label}]{{{d.fen}}}\n"


def _mainline(run) -> str:
    """Moves of the game in bold, pieces as chess figures (chessfss, loaded by chessboard)."""
    out, first = [], True
    for move, mark in run:
        number = (f"{move.number}." if move.white else (f"{move.number}..." if first else ""))
        out.append(number + figurine(move.san) + mark)
        first = False
    return "\\moves{" + " ".join(out) + "}"


def _line(items) -> str:
    """Moves in bold, comments in plain text, as in Dvoretsky's Endgame Manual."""
    out = []
    for kind, value in items:
        if kind == "diagram":
            out.append(_diagram(value))
        elif kind == "moves":
            out.append(_mainline(value))
        elif kind == "seen":
            out.append(f"\\seen{{{value}}}")
        elif kind in ("note", "end"):
            # notes are written in LaTeX; engine comments contain no special characters
            out.append(value + "\\par")
    return "\n".join(out)


def _game_head(g: dict) -> str:
    elo = lambda v: f" ({v})" if v else ""
    surname = lambda name: name.split(",")[0].strip()
    year = g["date"][:4] if g["date"][:4].isdigit() and g["date"][:4] not in g["event"] else ""
    pace = (f" ({g['time_control']})" if g["time_control"] in ("blitz", "rapid")
            and g["time_control"] not in g["event"].lower() else "")
    return (f"\\game{{{esc(surname(g['white']))}{elo(g['white_elo'])}}}"
            f"{{{esc(surname(g['black']))}{elo(g['black_elo'])}}}"
            f"{{{esc(g['event'])}{', ' + year if year else ''}{esc(pace)}}}\n")


def positions_latex(entries) -> str:
    """The positions as LaTeX to paste into the book: needs the packages and colours of PREAMBLE."""
    return ("% Positions written by list_positions. Uses the macros \\game, \\diagram, \\moves, \\seen\n"
            "% and \\K \\Q \\R \\B \\N from the preamble of report.tex.\n\n" + _positions(entries) + "\n")


def _positions(entries) -> str:
    """Each position: the game, its diagram, and the rest of the game."""
    return "\n".join(_game_head(p.game) + _line(items) for p, items in entries)


def _table(header: List[str], body: List[List[str]], align: str) -> str:
    lines = [f"\\begin{{tabular}}{{{align}}}", "\\toprule",
             " & ".join(f"\\textbf{{{esc(h)}}}" for h in header) + r" \\", "\\midrule"]
    lines += [" & ".join(esc(c) for c in row) + r" \\" for row in body]
    lines += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(lines) + "\n"


def render(s: Summary, min_games: int, top: int, rook_chapter: Optional[str] = None) -> str:
    def head(key):
        title, intro = texts.SECTIONS[key]
        return (f"\\newpage\n\\section*{{{esc(title)}}}\n"
                f"{{\\color{{muted}}{esc(intro.format(min_games=min_games))}\\par}}\n\\vspace{{8pt}}\n")

    out = [PREAMBLE,
           f"{{\\LARGE\\bfseries {esc(texts.title(s))}\\par}}\n\\vspace{{4pt}}\n"
           f"{{\\large\\color{{muted}}{esc(texts.subtitle(s))}\\par}}\n",
           "\\section*{Introduction}\n" + "\n\n".join(esc(p) for p in texts.introduction(s)) + "\n",
           f"\\subsection*{{The data}}\n\\begin{{tabular}}{{@{{}}{LEFT}p{{5cm}}{LEFT}p{{11cm}}@{{}}}}\n" +
           "\n".join(f"\\textcolor{{muted}}{{{esc(a)}}} & {esc(b)} \\\\" for a, b in texts.data_lines(s)) +
           "\n\\end{tabular}\n",
           f"\\subsection*{{Words used in this book}}\n\\begin{{tabular}}{{@{{}}{LEFT}p{{3.6cm}}{LEFT}p{{12.4cm}}@{{}}}}\n" +
           "\n".join(f"\\textbf{{{esc(a)}}} & {esc(b)} \\\\[3pt]" for a, b in texts.definitions(min_games)) +
           "\n\\end{tabular}\n",
           head("common") + _chart(sections.most_common(s, top), lambda r: r.per_100_games,
                                   lambda r: f"{r.per_100_games:.1f} of 100  ({r.games:,} games)"),
           head("tricky") + _chart(sections.trickiest(s, min_games, top), lambda r: r.blunders_per_100,
                                   lambda r: f"{r.blunders_per_100:.0f}  ({r.blunders:,} in {r.games:,} games)") +
           f"\n\\vspace{{6pt}}{{\\footnotesize\\color{{muted}}{sections.unranked(s, min_games)} other materials "
           f"were reached in fewer than {min_games} games and are not ranked.\\par}}\n",
           head("overall") + _chart(sections.most_blunders_overall(s, OVERALL_TOP), lambda r: r.blunders_per_100_all,
                                    lambda r: f"{r.blunders_per_100_all:.1f}  (in {r.per_100_games:.1f} of 100 games, {r.blunders_per_100:.0f} blunders per 100 of them)", width="7cm"),
           (f"\\newpage\n\\section*{{{esc(texts.SECTIONS['example'][0])}}}\n"
            f"{{\\color{{muted}}{esc(texts.SECTIONS['example'][1])}\\par}}\n"
            f"\\input{{{rook_chapter}}}\n") if rook_chapter else "",
           "\\end{document}\n"]
    return "\n".join(out)
