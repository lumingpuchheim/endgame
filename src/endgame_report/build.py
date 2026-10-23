"""Statistics chapter from the data, and the positions with their games."""

import logging
import os
import re
from typing import Dict, Optional

from . import latex
from .collect import collect
from .game_line import Shown, build_line
from .notes import load_notes
from .reader import find_files, read_moves
from .stats import summarize

logger = logging.getLogger(__name__)
STATISTICS = os.path.join("chapters", "statistics.tex")


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


def write_statistics(input_dir: str, out_file: str = STATISTICS, min_elo: Optional[int] = None,
                     min_games: int = 500, top: int = 25) -> str:
    """Read the data once and write the introduction and chapters 1-3 to out_file."""
    games, segments, blunders, _counts = collect(input_dir)
    summary = summarize(games, segments, blunders, min_elo)
    os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as handle:
        handle.write(latex.render_statistics(summary, min_games, top))
    logger.info("%d games. Written: %s", summary.games, out_file)
    return out_file
