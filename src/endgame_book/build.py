"""Part I and the appendix from the data, and the positions with their games."""

import logging
import os
from collections import Counter
import re
from typing import List, Optional

from . import latex
from .collect import collect
from .game_line import Shown, build_line
from .notes import load_notes, position_key
from .reader import find_files, read_moves
from .sections import MANY, section_of
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


def skipped_positions(notes) -> set:
    """Positions you do not want in the book: a note '@ <FEN> | skip'."""
    return {key for key, move in notes if move == "skip"}


def position_entries(input_dir: str, shown_positions, notes_dir: str = "notes",
                     limit: Optional[int] = None, per_section: Optional[int] = None,
                     shown: Optional[Shown] = None, keep_noted: bool = False, section_caps=None) -> list:
    """With keep_noted, positions you wrote a note for (on the diagram's position) are chosen
    first, so a rewritten chapter never loses them; the chapter still shows them in the usual order."""
    if keep_noted and shown_positions:
        import copy
        from .notes import load_notes, position_key
        noted = {key for key, move in load_notes(notes_dir) if move != "skip"}
        first = sorted(range(len(shown_positions)),
                       key=lambda i: (position_key(shown_positions[i].blunder["fen"]) not in noted, i))
        trial = _entries(input_dir, [shown_positions[i] for i in first], notes_dir, limit, per_section,
                         copy.deepcopy(shown) if shown is not None else None, always=noted,
                         section_caps=section_caps)
        chosen = {id(p) for p, _items in trial}
        return _entries(input_dir, [p for p in shown_positions if id(p) in chosen], notes_dir, None, None, shown)
    return _entries(input_dir, shown_positions, notes_dir, limit, per_section, shown, section_caps=section_caps)


def _entries(input_dir: str, shown_positions, notes_dir: str = "notes",
             limit: Optional[int] = None, per_section: Optional[int] = None,
             shown: Optional[Shown] = None, always=frozenset(), section_caps=None) -> list:
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
    notes = load_notes(notes_dir)
    skipped = skipped_positions(notes)
    shown = shown if shown is not None else Shown()
    games_shown, entries, in_section = set(), [], Counter()
    # The section with many pawns always gets its share (at least per_section): the simple sections
    # share the rest evenly, so every simple pawn balance is shown; places they cannot fill go to it.
    simple_cap = per_section
    if limit is not None and per_section is not None:
        found_sections = {section_of(p.blunder["fen"]) for p in shown_positions}
        simple_sections = len(found_sections - {MANY})
        room = limit - per_section if MANY in found_sections else limit
        if simple_sections:
            simple_cap = min(per_section, max(1, room // simple_sections))
        # A section given more places (section_caps) gets them on top: the chapter grows.
        section_caps = {s: c for s, c in (section_caps or {}).items() if s in found_sections}
        limit += sum(max(0, c - simple_cap) for c in section_caps.values())
    for pos in shown_positions:
        key = position_key(pos.blunder["fen"])
        if key in skipped:                                       # "@ <FEN> | skip" in notes/
            continue
        section = section_of(pos.blunder["fen"])
        # Your annotated positions count like the others, but always get in: a full section grows.
        if key not in always:
            if limit is not None and len(entries) >= limit:
                continue
            cap = (section_caps or {}).get(section, simple_cap)
            if section != MANY and cap is not None and in_section[section] >= cap:
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
