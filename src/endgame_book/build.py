"""Part I and the appendix from the data, and the positions with their games."""

import logging
import os
import re
from typing import List, Optional

from . import latex
from .collect import collect
from .game_line import Shown, build_line
from .notes import load_notes
from .reader import find_files, read_moves
from .stats import summarize

logger = logging.getLogger(__name__)
CHAPTERS = "chapters"
PART_ONE = "where-the-mistakes-are.tex"
APPENDIX = "how-the-numbers-were-made.tex"


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


def write_statistics(input_dir: str, chapters_dir: str = CHAPTERS, min_elo: Optional[int] = None,
                     min_games: int = 500, top: int = 15) -> List[str]:
    """Read the data once; write Part I (chapters 1-3) and the appendix into chapters_dir."""
    games, segments, blunders, _counts = collect(input_dir)
    summary = summarize(games, segments, blunders, min_elo)
    os.makedirs(chapters_dir, exist_ok=True)
    written = []
    for name, text in ((PART_ONE, latex.render_part_one(summary, min_games, top)),
                       (APPENDIX, latex.render_appendix(summary, min_games))):
        path = os.path.join(chapters_dir, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        written.append(path)
    logger.info("%d games. Written: %s", summary.games, ", ".join(written))
    return written
