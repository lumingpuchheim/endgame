"""LaTeX for the book: the statistics chapters and the positions."""

import re
from typing import List, Optional
from urllib.parse import quote

from . import sections, texts
from .game_line import Diagram, figurine
from .stats import Summary

_SPECIAL = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
            "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def esc(text) -> str:
    """Escape LaTeX specials; 'chapter <<label>>' becomes \\xref{chapter}{label}, a link on both words."""
    out = "".join(_SPECIAL.get(ch, ch) for ch in str(text))
    return re.sub(r"(\w+) <<([A-Za-z0-9:_-]+)>>", r"\\xref{\1}{\2}", out)



LEFT = r">{\raggedright\arraybackslash}"


OVERALL_TOP = 15


def _chart(rows, value, label, width: str = "8cm", empty: str = "No games in this band yet.") -> str:
    """Horizontal bars drawn by pgfplots from the numbers written here; `empty` when there are none."""
    if not rows:
        return "\\textit{" + esc(empty) + "}\n"
    rows = rows[::-1]                     # pgfplots draws bottom-up; keep the first row on top
    names = ",".join("{" + esc(texts.material_name(r.key)) + "}" for r in rows)
    coords = " ".join(f"({value(r):.3f},{i})" for i, r in enumerate(rows))
    side = "\n".join(f"\\node[anchor=west,font=\\footnotesize,text=muted] at "
                     f"(axis description cs:1.02,{(i + 0.5) / len(rows):.4f}) {{{esc(label(r))}}};"
                     for i, r in enumerate(rows))
    height = max(5.0, min(23.0, 0.8 * len(rows) + 1.5))
    return (f"\\begin{{tikzpicture}}\n\\begin{{axis}}[xbar,width={width},height={height:.1f}cm,xmin=0,"
            f"ytick={{0,...,{len(rows) - 1}}},yticklabels={{{names}}},"
            f"ymin=-0.5,ymax={len(rows) - 0.5},enlarge y limits=false,bar width=7pt,"
            f"xmajorgrids,grid style={{gray!20}},axis x line*=bottom,axis y line*=left,"
            f"tick label style={{font=\\footnotesize}},clip=false]\n"
            f"\\addplot[fill=bar,draw=none] coordinates {{{coords}}};\n"
            f"{side}\n\\end{{axis}}\n\\end{{tikzpicture}}\n")


def lichess_url(fen: str) -> str:
    """Lichess analysis board for a FEN (spaces become underscores)."""
    return "https://lichess.org/analysis/standard/" + quote(fen.replace(" ", "_"), safe="/_-")


def _diagram(d: Diagram) -> str:
    return f"\\diagram[{d.label}]{{{d.fen}}}\n"


def _mainline(run) -> str:
    """Moves of the game in bold, pieces as chess figures (chessfss, loaded by chessboard)."""
    out, first = [], True
    for move, mark in run:
        number = (f"{move.number}." if move.white else (f"{move.number}..." if first else ""))
        out.append(number + figurine(move.san).replace("#", "\\#") + mark)   # mate sign
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
    """The positions for a chapter of the book, one section per pawn balance
    (rook and two pawns vs rook, rook and pawn vs rook and pawn, ...). Uses the macros of endgame.sty."""
    out = ["% Positions written by list_positions. Write your comments between the lines;",
           "% pieces as \\K \\Q \\R \\B \\N, e.g. 59...\\R e5!. Macros: endgame.sty.", ""]
    section_now = None
    for pos, items in entries:
        split = sections.pawn_split(pos.blunder["fen"])
        if split != section_now:
            section_now = split
            count = sum(1 for p, _ in entries if sections.pawn_split(p.blunder["fen"]) == split)
            out.append(f"\\section{{{texts.pawns_title(split)}}}")
            out.append(f"{count} position{'s' if count != 1 else ''}.\n")
        out.append(_game_head(pos.game) + _line(items))
    return "\n".join(out) + "\n"


def _paragraphs(texts_: List[str]) -> str:
    return "\n\n".join(esc(t) for t in texts_) + "\n\n"


def _points(points: List[str]) -> str:
    if not points:
        return ""
    return ("\\begin{keypoints}\n" + "\n".join(f"\\item {esc(p)}" for p in points) +
            "\n\\end{keypoints}\n")


def _figure(chart: str) -> str:
    return "\\begin{center}\n" + chart + "\\end{center}\n"


GENERATED = ""   # make.py adds the header that tells a generated file from an edited one


def render_part_one(s: Summary, min_games: int, top: int, has_chapters: bool = True,
                    pawns_first: bool = False) -> str:
    """Chapters 1-3 of Part I: which endgames happen, which go wrong, where to start."""
    common = sections.most_common(s, top)
    tricky = sections.trickiest(s, min_games, top)
    overall = sections.most_blunders_overall(s, OVERALL_TOP)
    return (GENERATED +
            "\\chapter{The Endgames You Will Meet}\\label{ch:meet}\n" + _paragraphs(texts.common_intro(s)) +
            _figure(_chart(common, lambda r: r.per_100_games,
                           lambda r: f"{r.per_100_games:.1f} of 100 games", width="6.5cm")) +
            _points(texts.common_points(common)) +
            "\\chapter{The Endgames That Go Wrong}\\label{ch:go-wrong}\n" + _paragraphs(texts.tricky_intro(s, min_games)) +
            _figure(_chart(tricky, lambda r: r.blunders_per_100,
                           lambda r: f"{r.blunders_per_100:.0f} per 100 games", width="6.5cm",
                           empty=texts.tricky_empty(s, min_games))) +
            _points(texts.tricky_points(tricky)) +
            "\\chapter{Where to Start}\\label{ch:where-to-start}\n" + _paragraphs(texts.overall_intro()) +
            _figure(_chart(overall, lambda r: r.blunders_per_100_all,
                           lambda r: f"{r.blunders_per_100_all:.1f} per 100 games", width="6.5cm")) +
            _points(texts.overall_points(overall, has_chapters, pawns_first)))


def render_appendix(s: Summary, min_games: int) -> str:
    """The data and the words used, for readers who want to check the numbers."""
    return (GENERATED + "\\chapter{How the Numbers Were Made}\\label{app:numbers}\n" +
            _paragraphs(["Every game was replayed and every endgame position checked by Stockfish. The "
                         "tables below say which games were used and what the words in Part <<part:mistakes>> mean."]) +
            "\\section{The data}\n"
            f"\\begin{{tabular}}{{@{{}}{LEFT}p{{4.6cm}}{LEFT}p{{11.4cm}}@{{}}}}\n" +
            "\n".join(f"\\textcolor{{muted}}{{{esc(a)}}} & {esc(b)} \\\\[2pt]" for a, b in texts.data_lines(s)) +
            "\n\\end{tabular}\n\n\\section{Words used in this book}\n"
            f"\\begin{{tabular}}{{@{{}}{LEFT}p{{4.6cm}}{LEFT}p{{11.4cm}}@{{}}}}\n" +
            "\n".join(f"\\textbf{{{esc(a)}}} & {esc(b)} \\\\[4pt]" for a, b in texts.definitions(min_games)) +
            "\n\\end{tabular}\n")
