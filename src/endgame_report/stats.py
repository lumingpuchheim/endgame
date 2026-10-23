"""The numbers behind the two questions, computed in memory from the collected rows."""

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# A material counts as reached only if it stands for at least this many moves (one by each side).
# Shorter states happen in the middle of an exchange and belong to the material before them.
MIN_SEGMENT_MOVES = 2


def material(signature: str) -> str:
    """Colour-neutral material: 'RN-RB' and 'RB-RN' both become 'RB v RN'; '' means pawns only."""
    sides = sorted((side or "pawns") for side in signature.split("-", 1))
    return " v ".join(sides)


def is_real_blunder(row: dict) -> bool:
    """A marked blunder counts only if the engine's best move differs from the move
    played and at least one move kept the position (holding >= 1)."""
    if row["move"] == row["best"]:
        return False
    return row["holding"] not in ("", "0")


def rate_range(events: int, base: int, per: int = 100) -> Tuple[float, float, float]:
    """Rate per `per` with an approximate 95% range (Poisson)."""
    if base == 0:
        return (0.0, 0.0, 0.0)
    rate = events / base * per
    spread = 1.96 * math.sqrt(events) / base * per if events else 3.0 / base * per
    return (rate, max(0.0, rate - spread), rate + spread)


def lasting_segments(segments: List[dict]) -> Dict[int, int]:
    """For one game's segments (in order): map each segment index to the segment it counts as.
    Short segments (exchanges in progress) count as the last lasting segment before them,
    or, at the very start, the first lasting one after them."""
    ordered = sorted(segments, key=lambda s: int(s["order"]))
    lasting = [int(s["order"]) for s in ordered if int(s["moves"]) >= MIN_SEGMENT_MOVES]
    mapping: Dict[int, int] = {}
    for s in ordered:
        index = int(s["order"])
        if index in lasting or not lasting:
            mapping[index] = index
            continue
        before = [i for i in lasting if i < index]
        mapping[index] = before[-1] if before else lasting[0]
    return mapping


@dataclass
class Row:
    key: str
    label: str
    games: int            # games that reached it (once per game)
    per_100_games: float  # reached in N of 100 games
    moves: int            # moves played in it
    blunders: int         # real blunders made in it
    blunders_per_100: float
    low: float
    high: float
    blunders_per_1000_moves: float


@dataclass
class Summary:
    games: int
    games_with_endgame: int
    marked_blunders: int
    real_blunders: int
    by_material: List[Row]
    sources: List[str]
    endgame_rule: str
    depth: str
    min_elo: Optional[int]


def _elo_ok(game: dict, min_elo: Optional[int]) -> bool:
    if min_elo is None:
        return True
    w, b = game["white_elo"], game["black_elo"]
    return w.isdigit() and b.isdigit() and int(w) >= min_elo and int(b) >= min_elo


def summarize(games: List[dict], segments: List[dict], blunders: List[dict],
              min_elo: Optional[int] = None) -> Summary:
    kept = {g["game_id"]: g for g in games if _elo_ok(g, min_elo)}
    total = len(kept)

    per_game: Dict[str, List[dict]] = defaultdict(list)
    for s in segments:
        if s["game_id"] in kept:
            per_game[s["game_id"]].append(s)

    reached: Dict[str, set] = defaultdict(set)
    moves: Counter = Counter()
    material_of: Dict[Tuple[str, int], str] = {}             # (game, segment) -> material
    for game_id, segs in per_game.items():
        mapping = lasting_segments(segs)
        by_index = {int(s["order"]): s for s in segs}
        for s in segs:
            key = material(by_index[mapping[int(s["order"])]]["signature"])
            material_of[(game_id, int(s["order"]))] = key
            reached[key].add(game_id)
            moves[key] += int(s["moves"])

    counted = [b for b in blunders if b["game_id"] in kept]
    real = [b for b in counted if is_real_blunder(b)]
    errors: Counter = Counter()
    for b in real:
        key = material_of.get((b["game_id"], int(b["segment"])))
        if key:
            errors[key] += 1

    rows = []
    for key, ids in reached.items():
        n, k, m = len(ids), errors[key], moves[key]
        rate, low, high = rate_range(k, n)
        rows.append(Row(key, key, n, n / total * 100 if total else 0.0, m, k, rate, low, high,
                        k / m * 1000 if m else 0.0))

    return Summary(
        games=total,
        games_with_endgame=sum(1 for g in kept.values() if g["endgame"] == "True"),
        marked_blunders=len(counted), real_blunders=len(real),
        by_material=sorted(rows, key=lambda r: -r.games),
        sources=sorted({g["source"] for g in kept.values()}),
        endgame_rule=", ".join(sorted({g["endgame_rule"] for g in kept.values()})),
        depth=", ".join(sorted({g["depth"] for g in kept.values()})), min_elo=min_elo,
    )
