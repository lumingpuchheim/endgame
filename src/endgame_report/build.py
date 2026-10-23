"""One run: annotated PGN files -> report.tex and report.pdf. Nothing else is kept."""

import logging
import os
import re
import shutil
import subprocess
from typing import Dict, Optional

from . import latex
from .collect import collect
from .game_line import Shown, build_line
from .notes import load_notes
from .reader import find_files, read_moves
from .sections import positions
from .stats import _elo_ok, summarize

logger = logging.getLogger(__name__)
LATEX_LEFTOVERS = (".aux", ".log", ".out")
ROOK_CHAPTER = os.path.join("chapters", "rook-endgames.tex")


def compile_pdf(tex_path: str) -> Optional[str]:
    """Run pdflatex next to the .tex file; remove its helper files. Returns the PDF path or None."""
    pdflatex = shutil.which("pdflatex")
    if not pdflatex:
        logger.warning("pdflatex not found: wrote the LaTeX file, no PDF. Install MiKTeX or TeX Live.")
        return None
    folder, name = os.path.split(os.path.abspath(tex_path))
    stem = os.path.splitext(name)[0]
    for _run in range(2):                 # the second run fills in diagram references
        result = subprocess.run([pdflatex, "-interaction=nonstopmode", "-halt-on-error", name],
                                cwd=folder, capture_output=True, text=True, errors="replace")
        if result.returncode != 0:
            tail = "\n".join(result.stdout.splitlines()[-15:])
            raise RuntimeError(f"pdflatex failed; see {os.path.join(folder, stem + '.log')}\n{tail}")
    for ext in LATEX_LEFTOVERS:
        leftover = os.path.join(folder, stem + ext)
        if os.path.exists(leftover):
            os.remove(leftover)
    return os.path.join(folder, stem + ".pdf")


def diagram_label(pos) -> str:
    """A readable LaTeX label, e.g. 'nakamura-leko-61w'."""
    slug = lambda name: re.sub(r"[^a-z0-9]+", "", name.split(",")[0].lower()) or "x"
    side = "w" if pos.blunder["mover"] == "white" else "b"
    return f"{slug(pos.game['white'])}-{slug(pos.game['black'])}-{pos.blunder['move_number']}{side}"


def position_entries(input_dir: str, shown_positions, notes_dir: str = "notes",
                     limit: Optional[int] = None) -> list:
    """(position, line) for each position: its diagram and the rest of the game. A later mistake
    in a game already shown from an earlier move is left out, and the next position takes its
    place, so `limit` positions are shown if there are that many."""
    if not shown_positions:
        return []
    try:
        import chess  # noqa: F401  (python-chess replays the games)
    except ImportError:
        raise RuntimeError("the positions need python-chess: py -m pip install chess")
    paths = {os.path.basename(p): p for p in find_files(input_dir)}
    notes, shown = load_notes(notes_dir), Shown()
    games_shown, entries = set(), []
    for pos in shown_positions:
        if limit is not None and len(entries) >= limit:
            break
        _headers, moves = read_moves(paths[pos.game["source"]], pos.game["game_id"])
        items = build_line(pos.blunder["fen"], moves, int(pos.blunder["ply"]), pos.game["result"], notes, shown,
                           diagram_label(pos))
        if items[0][0] == "seen" and pos.game["game_id"] in games_shown:
            continue
        games_shown.add(pos.game["game_id"])
        entries.append((pos, items))
    return entries


def build(input_dir: str, out_dir: str, name: str = "report", min_elo: Optional[int] = None,
          min_games: int = 500, top: int = 25, pdf: bool = True,
          notes_dir: str = "notes", max_positions: Optional[int] = 50,
          rook_chapter: str = ROOK_CHAPTER) -> Dict[str, str]:
    games, segments, blunders, _counts = collect(input_dir)
    summary = summarize(games, segments, blunders, min_elo)
    kept = {g["game_id"] for g in games if _elo_ok(g, min_elo)}
    if os.path.exists(rook_chapter):
        logger.info("Rook endings: using your %s", rook_chapter)
    else:                                  # first build: write the positions once; never overwritten
        all_positions, _found = positions(games, blunders, kept)
        entries = position_entries(input_dir, all_positions, notes_dir, max_positions)
        os.makedirs(os.path.dirname(os.path.abspath(rook_chapter)), exist_ok=True)
        with open(rook_chapter, "w", encoding="utf-8") as handle:
            handle.write(latex.positions_latex(entries))
        logger.info("Rook endings: wrote %d positions to %s", len(entries), rook_chapter)
    os.makedirs(out_dir, exist_ok=True)
    written = {}
    tex_path = os.path.join(out_dir, name + ".tex")
    chapter = os.path.relpath(os.path.abspath(rook_chapter), os.path.abspath(out_dir)).replace(os.sep, "/")
    with open(tex_path, "w", encoding="utf-8") as handle:
        handle.write(latex.render(summary, min_games, top, chapter))
    written["tex"] = tex_path
    if pdf:
        pdf_path = compile_pdf(tex_path)
        if pdf_path:
            written["pdf"] = pdf_path
    logger.info("%d games in the report. Written: %s", summary.games, ", ".join(written.values()))
    return written
