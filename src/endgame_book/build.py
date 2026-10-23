"""Part I and the appendix from the data, and the positions with their games."""

import logging
import os
from collections import Counter
import re
from typing import List, Optional

from . import latex
from .game_line import Shown, build_line, plain_text
from .notes import load_notes
from .reader import find_files, read_moves
from .sections import pawn_split, positions
from .stats import _elo_ok, summarize
from .texts import pawns_title

logger = logging.getLogger(__name__)
CHAPTERS = "chapters"
ROOK_CHAPTER = "rook-endgames.tex"
PART_ONE = "where-the-mistakes-are.tex"
APPENDIX = "how-the-numbers-were-made.tex"


def diagram_label(pos) -> str:
    """A readable LaTeX label, e.g. 'nakamura-leko-61w'."""
    slug = lambda name: re.sub(r"[^a-z0-9]+", "", name.split(",")[0].lower()) or "x"
    side = "w" if pos.blunder["mover"] == "white" else "b"
    return f"{slug(pos.game['white'])}-{slug(pos.game['black'])}-{pos.blunder['move_number']}{side}"


def position_entries(input_dir: str, shown_positions, notes_dir: str = "notes",
                     limit: Optional[int] = None, per_section: Optional[int] = None) -> list:
    """(position, line) for each position: its diagram and the rest of the game. At most `limit`
    positions in all and at most `per_section` for each pawn balance (rook and two pawns vs rook,
    ...). A later mistake in a game already shown from an earlier move is left out, and the next
    position takes its place."""
    if not shown_positions:
        return []
    try:
        import chess  # noqa: F401  (python-chess replays the games)
    except ImportError:
        raise RuntimeError("the positions need python-chess: py -m pip install chess")
    paths = {os.path.basename(p): p for p in find_files(input_dir)}
    notes, shown = load_notes(notes_dir), Shown()
    games_shown, entries, in_section = set(), [], Counter()
    for pos in shown_positions:
        if limit is not None and len(entries) >= limit:
            break
        section = pawn_split(pos.blunder["fen"])
        if per_section is not None and in_section[section] >= per_section:
            continue
        _headers, moves = read_moves(paths[pos.game["source"]], pos.game["game_id"])
        items = build_line(pos.blunder["fen"], moves, int(pos.blunder["ply"]), pos.game["result"], notes, shown,
                           diagram_label(pos))
        if items[0][0] == "seen" and pos.game["game_id"] in games_shown:
            continue
        games_shown.add(pos.game["game_id"])
        in_section[section] += 1
        entries.append((pos, items))
    return entries


def write_statistics(games, segments, blunders, chapters_dir: str = CHAPTERS, min_elo: Optional[int] = None,
                     min_games: int = 500, top: int = 15) -> List[str]:
    """Write Part I (chapters 1-3) and the appendix into chapters_dir. Returns the files written."""
    summary = summarize(games, segments, blunders, min_elo)
    os.makedirs(chapters_dir, exist_ok=True)
    written = []
    for name, text in ((PART_ONE, latex.render_part_one(summary, min_games, top)),
                       (APPENDIX, latex.render_appendix(summary, min_games))):
        path = os.path.join(chapters_dir, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        written.append(path)
    return written


def write_positions(input_dir: str, games, blunders, out_file: str, min_elo: Optional[int] = None,
                    show: Optional[int] = 20, per_section: Optional[int] = None, material: str = "R v R",
                    notes_dir: str = "notes", echo: bool = True) -> list:
    """Write the simplest positions of one material, with the rest of each game, to out_file.
    With echo, print the counts per pawn balance and every position. Returns the entries."""
    kept = {g["game_id"] for g in games if _elo_ok(g, min_elo)}
    found, total = positions(games, blunders, kept, wanted=material)
    entries = position_entries(input_dir, found, notes_dir, show, per_section)
    if echo:
        print(f"{len(kept):,} games, {total:,} positions with a blunder in {material}.\n")
        counts = Counter(pawn_split(p.blunder["fen"]) for p in found)
        shown = Counter(pawn_split(p.blunder["fen"]) for p, _ in entries)
        print(f"{'Found':>7} {'Written':>8}  Pawn balance, simplest first")
        for split in dict.fromkeys(pawn_split(p.blunder["fen"]) for p in found):
            print(f"{counts[split]:>7,} {shown[split]:>8,}  {pawns_title(split)}")
        for i, (p, items) in enumerate(entries, 1):
            g = p.game
            print(f"\n{i:>4}. {pawns_title(pawn_split(p.blunder['fen']))}, "
                  f"{'White' if p.blunder['mover'] == 'white' else 'Black'} to move. "
                  f"{g['white']} - {g['black']}, {g['event']} {g['date'][:4]}")
            print(f"      {latex.lichess_url(p.blunder['fen'])}")
            print(f"      {plain_text(items)}")
    folder = os.path.dirname(os.path.abspath(out_file))
    os.makedirs(folder, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as handle:
        handle.write(latex.positions_latex(entries))
    return entries
