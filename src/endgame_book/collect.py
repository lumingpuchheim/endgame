"""Read all annotated PGN files under the input folder into memory. What was read from each file is
kept in cache/ and used again while the file stays the same, so only new or changed files are read."""

import dataclasses
import hashlib
import logging
import os
import pickle
from typing import Dict, List, Set, Tuple

from .reader import find_files, iter_games

logger = logging.getLogger(__name__)


def _text(value) -> str:
    return "" if value is None else str(value)


CACHE_DIR = "cache"


def _code_check() -> str:
    """The cache is only valid for the reading code that wrote it."""
    here = os.path.dirname(os.path.abspath(__file__))
    digest = hashlib.sha1()
    for name in ("collect.py", "reader.py"):
        with open(os.path.join(here, name), "rb") as handle:
            digest.update(handle.read().replace(b"\r\n", b"\n"))
    return digest.hexdigest()[:12]


def _read_file(path: str) -> list:
    """(game row, segments, blunders, endgame rule, depth) for each game in one file."""
    out = []
    for game in iter_games(path):
        row = {f.name: _text(getattr(game, f.name)) for f in dataclasses.fields(game)
               if f.name not in ("segments", "blunders")}
        segments = [{"game_id": game.game_id, **{k: _text(v) for k, v in dataclasses.asdict(s).items()}}
                    for s in game.segments]
        blunders = [{"game_id": game.game_id, **{k: _text(v) for k, v in dataclasses.asdict(b).items()}}
                    for b in game.blunders]
        out.append((row, segments, blunders, game.endgame_rule, game.depth))
    return out


def _cached_file(path: str, code: str, cache_dir: str) -> Tuple[list, bool]:
    """The games of one file, from the cache if the file has not changed since. (games, from cache?)"""
    stat = os.stat(path)
    stamp = (os.path.abspath(path), stat.st_size, stat.st_mtime_ns, code)
    name = hashlib.sha1(os.path.abspath(path).encode()).hexdigest()[:16] + ".pickle"
    cache_path = os.path.join(cache_dir, name)
    try:
        with open(cache_path, "rb") as handle:
            saved_stamp, games = pickle.load(handle)
        if saved_stamp == stamp:
            return games, True
    except (OSError, EOFError, pickle.UnpicklingError, ValueError, TypeError):
        pass
    games = _read_file(path)
    try:
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_path + ".tmp", "wb") as handle:
            pickle.dump((stamp, games), handle, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(cache_path + ".tmp", cache_path)
    except OSError as exc:
        logger.warning("could not write the cache for %s: %s", path, exc)
    return games, False


def collect(input_dir: str, cache_dir: str = CACHE_DIR) -> Tuple[List[dict], List[dict], List[dict], Dict[str, int]]:
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
    read = 0
    code = _code_check()
    for number, path in enumerate(files, 1):
        file_games, from_cache = _cached_file(path, code, cache_dir)
        read += not from_cache
        for row, game_segments, game_blunders, rule, depth in file_games:
            if row["game_id"] in seen:          # the same game in two TWIC issues
                duplicates += 1
                continue
            seen.add(row["game_id"])
            rules.add(rule)
            depths.add(depth)
            games.append(row)
            segments.extend(game_segments)
            blunders.extend(game_blunders)
        if number % 50 == 0:
            logger.info("%d of %d files read, %d games", number, len(files), len(games))
    if len(rules) > 1 or len(depths) > 1:
        raise ValueError(f"input mixes settings: endgame rules {sorted(rules)}, depths {sorted(depths)}. "
                         "Link only files made with one setting into the input folder.")
    counts = {"files": len(files), "games": len(games), "duplicates": duplicates}
    logger.info("Read %d files (%d new or changed, the rest from cache/): %d games (%d duplicates skipped)",
                len(files), read, len(games), duplicates)
    return games, segments, blunders, counts
