"""One program for the whole book: python -m endgame_book [options]

Each run:
  1. Statistics (Part I and the appendix): written when missing, or when the data or the
     settings changed since they were written. A file you have edited is never replaced;
     you get a warning instead when its numbers are out of date.
  2. Rook chapter: written only when missing. After that it is yours.
The data is read only when something has to be written. scripts/make_book.bat then
compiles book.tex.
"""

import hashlib
import logging
import os
import re
from typing import List, Optional, Tuple

from . import latex
from .build import APPENDIX, CHAPTERS, PART_ONE, position_entries
from .collect import collect
from .reader import find_files
from .sections import positions
from .stats import _elo_ok, summarize

logger = logging.getLogger(__name__)
ROOK_CHAPTER = "rook-endgames.tex"
_STAMP = re.compile(r"^% Written by make_book from the data \((.*); check ([0-9a-f]{12})\)")


def _check(body: str) -> str:
    """Checksum of a file's text, the same whatever line endings an editor used."""
    lines = [line.rstrip() for line in body.replace("\r\n", "\n").split("\n")]
    return hashlib.sha1("\n".join(lines).strip().encode("utf-8")).hexdigest()[:12]


def stamped(body: str, settings: str) -> str:
    return (f"% Written by make_book from the data ({settings}; check {_check(body)})\n"
            "% If you edit this file, make_book keeps your version.\n" + body)


def file_state(path: str) -> Tuple[str, str]:
    """('missing' | 'edited' | 'generated', settings it was written with)."""
    if not os.path.exists(path):
        return "missing", ""
    with open(path, encoding="utf-8") as handle:
        first = handle.readline()
        handle.readline()                       # the second stamp line
        body = handle.read()
    if first.startswith("% Written by scripts/update_statistics.bat"):
        return "generated", ""                  # written by the earlier version, never edited
    match = _STAMP.match(first)
    if not match or match.group(2) != _check(body):
        return "edited", match.group(1) if match else ""
    return "generated", match.group(1)


def make(input_dir: str, chapters_dir: str = CHAPTERS, min_elo: Optional[int] = None, min_games: int = 500,
         top: int = 15, show: Optional[int] = 50, per_section: Optional[int] = None,
         keep_statistics: bool = False) -> List[str]:
    """Bring the chapter files up to date. Returns one line per file saying what happened.
    With keep_statistics, existing statistics files are kept as they are, even if out of date."""
    data_files = find_files(input_dir)
    if not data_files:
        raise FileNotFoundError(f"no *.annotated.pgn files under {input_dir}")
    data_time = max(os.path.getmtime(p) for p in data_files)
    settings = f"min-elo {min_elo or 'any'}, min-games {min_games}, top {top}"
    os.makedirs(chapters_dir, exist_ok=True)

    report: List[str] = []
    stats_todo = []
    for name in (PART_ONE, APPENDIX):
        path = os.path.join(chapters_dir, name)
        state, written_with = file_state(path)
        stale = state != "missing" and (os.path.getmtime(path) < data_time or written_with != settings)
        if keep_statistics and state != "missing":
            report.append(f"kept      {path}  (--keep-statistics)")
        elif state == "missing" or (state == "generated" and stale):
            stats_todo.append(name)
        elif state == "edited" and stale:
            report.append(f"kept      {path}  WARNING: you edited it, and the data or the settings have changed "
                          "since. To get new numbers, rename or delete it and run make_book again.")
        else:
            report.append(f"kept      {path}  ({'yours' if state == 'edited' else 'up to date'})")

    rook = os.path.join(chapters_dir, ROOK_CHAPTER)
    rook_todo = not os.path.exists(rook)
    if not rook_todo:
        report.append(f"kept      {rook}  (yours)")

    if stats_todo or rook_todo:
        logger.info("Reading the data ...")
        games, segments, blunders, _counts = collect(input_dir)
        if stats_todo:
            summary = summarize(games, segments, blunders, min_elo)
            texts = {PART_ONE: latex.render_part_one(summary, min_games, top),
                     APPENDIX: latex.render_appendix(summary, min_games)}
            for name in stats_todo:
                path = os.path.join(chapters_dir, name)
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(stamped(texts[name], settings))
                report.append(f"written   {path}")
        if rook_todo:
            kept = {g["game_id"] for g in games if _elo_ok(g, min_elo)}
            found, _total = positions(games, blunders, kept)
            entries = position_entries(input_dir, found, "notes", show, per_section)
            with open(rook, "w", encoding="utf-8") as handle:
                handle.write(latex.positions_latex(entries))
            report.append(f"written   {rook}  ({len(entries)} positions)")
    return report
