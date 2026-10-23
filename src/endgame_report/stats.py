"""Step 2a: the numbers behind the two questions, computed from the CSV tables only."""

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional

TYPE_NAMES = {
    "rook": "Rook vs rook",
    "queen": "Queen vs queen",
    "knight": "Knight vs knight",
    "bishop_same": "Bishops, same colour",
    "bishop_opposite": "Bishops, opposite colour",
    "bishop_knight": "Bishop vs knight",
    "pawn": "Pawns only",
    "piece_vs_pawns": "Pieces vs pawns only",
    "mixed": "Other material (2-3 pieces a side)",
}


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


def rate_range(events: int, base: int, per: int = 100) -> tuple:
    """Rate per `per` with an approximate 95% range (Poisson)."""
    if base == 0:
        return (0.0, 0.0, 0.0)
    rate = events / base * per
    spread = 1.96 * math.sqrt(events) / base * per if events else 3.0 / base * per
    return (rate, max(0.0, rate - spread), rate + spread)


@dataclass
class Row:
    key: str
    label: str
    games: int            # games that reached it (once per game)
    per_100_games: float  # reached in N of 100 games
    moves: int            # judged moves played in it
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
    by_type: List[Row]
    by_signature: List[Row]
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
    reached: Dict[str, Dict[str, set]] = {"type": defaultdict(set), "signature": defaultdict(set)}
    moves: Dict[str, Counter] = {"type": Counter(), "signature": Counter()}
    for s in segments:
        if s["game_id"] not in kept:
            continue
        for level, key in (("type", s["kind"]), ("signature", material(s["signature"]))):
            reached[level][key].add(s["game_id"])
            moves[level][key] += int(s["moves"])
    counted = [b for b in blunders if b["game_id"] in kept]
    real = [b for b in counted if is_real_blunder(b)]
    errors: Dict[str, Counter] = {"type": Counter(), "signature": Counter()}
    for b in real:
        errors["type"][b["kind"]] += 1
        errors["signature"][material(b["signature"])] += 1

    def rows(level: str) -> List[Row]:
        result = []
        for key, ids in reached[level].items():
            n = len(ids)
            rate, low, high = rate_range(errors[level][key], n)
            m = moves[level][key]
            result.append(Row(key, TYPE_NAMES.get(key, key) if level == "type" else key, n,
                              n / total * 100 if total else 0.0, m, errors[level][key], rate, low, high,
                              errors[level][key] / m * 1000 if m else 0.0))
        return sorted(result, key=lambda r: -r.games)

    rules = sorted({g["endgame_rule"] for g in kept.values()})
    depths = sorted({g["depth"] for g in kept.values()})
    return Summary(
        games=total,
        games_with_endgame=sum(1 for g in kept.values() if g["endgame"] == "True"),
        marked_blunders=len(counted), real_blunders=len(real),
        by_type=rows("type"), by_signature=rows("signature"),
        sources=sorted({g["source"] for g in kept.values()}),
        endgame_rule=", ".join(rules), depth=", ".join(depths), min_elo=min_elo,
    )
