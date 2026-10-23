"""Read all annotated PGN files under the input folder into memory (nothing is written)."""

import dataclasses
import logging
from typing import Dict, List, Set, Tuple

from .reader import find_files, iter_games

logger = logging.getLogger(__name__)


def _text(value) -> str:
    return "" if value is None else str(value)


def collect(input_dir: str) -> Tuple[List[dict], List[dict], List[dict], Dict[str, int]]:
    """Games, endgame segments and blunders as lists of dicts, plus counts."""
    files = find_files(input_dir)
    if not files:
        raise FileNotFoundError(f"no *.annotated.pgn files under {input_dir}")
    games: List[dict] = []
    segments: List[dict] = []
    blunders: List[dict] = []
    seen: Set[str] = set()
    rules: Set[str] = set()
    depths: Set[str] = set()
    duplicates = 0
    for number, path in enumerate(files, 1):
        for game in iter_games(path):
            if game.game_id in seen:          # the same game in two TWIC issues
                duplicates += 1
                continue
            seen.add(game.game_id)
            rules.add(game.endgame_rule)
            depths.add(game.depth)
            row = {f.name: _text(getattr(game, f.name)) for f in dataclasses.fields(game)
                   if f.name not in ("segments", "blunders")}
            games.append(row)
            for s in game.segments:
                segments.append({"game_id": game.game_id, **{k: _text(v) for k, v in dataclasses.asdict(s).items()}})
            for b in game.blunders:
                blunders.append({"game_id": game.game_id, **{k: _text(v) for k, v in dataclasses.asdict(b).items()}})
        if number % 50 == 0:
            logger.info("%d of %d files read, %d games", number, len(files), len(games))
    if len(rules) > 1 or len(depths) > 1:
        raise ValueError(f"input mixes settings: endgame rules {sorted(rules)}, depths {sorted(depths)}. "
                         "Link only files made with one setting into the input folder.")
    counts = {"files": len(files), "games": len(games), "duplicates": duplicates}
    logger.info("Read %d files: %d games (%d duplicates skipped)", len(files), len(games), duplicates)
    return games, segments, blunders, counts
