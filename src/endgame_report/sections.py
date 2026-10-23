"""The rows each section shows, chosen once and used by every output format."""

from dataclasses import dataclass
from typing import Dict, List, Optional

from .stats import Row, Summary, is_real_blunder, material


def most_common(s: Summary, top: int) -> List[Row]:
    return sorted(s.by_material, key=lambda r: -r.games)[:top]


def trickiest(s: Summary, min_games: int, top: int) -> List[Row]:
    return sorted([r for r in s.by_material if r.games >= min_games], key=lambda r: -r.blunders_per_100)[:top]


def most_blunders_overall(s: Summary, top: int) -> List[Row]:
    return sorted(s.by_material, key=lambda r: -r.blunders_per_100_all)[:top]


def unranked(s: Summary, min_games: int) -> int:
    return sum(1 for r in s.by_material if r.games < min_games)


def pieces_on_board(fen: str) -> int:
    """All pieces on the board, kings and pawns included."""
    return sum(ch.isalpha() for ch in fen.split()[0])


@dataclass
class ExampleGame:
    game: dict
    blunders: List[dict]     # all real blunders of the game, in move order
    pieces: int              # pieces on the board at its simplest rook-ending blunder
    candidates: int          # rook-ending blunders the game was chosen from


def simplest_game(games: List[dict], blunders: List[dict], kept_ids: set,
                  wanted: str = "R v R") -> Optional[ExampleGame]:
    """The game with the real blunder in `wanted` material that has the fewest pieces on the
    board. Ties: fewer moves that would have held, then the earlier game in the input."""
    by_id: Dict[str, dict] = {g["game_id"]: g for g in games}
    order = {g["game_id"]: i for i, g in enumerate(games)}
    real = [b for b in blunders if b["game_id"] in kept_ids and is_real_blunder(b) and b["fen"]]
    pool = [b for b in real if material(b["signature"]) == wanted]
    if not pool:
        return None
    best = min(pool, key=lambda b: (pieces_on_board(b["fen"]), int(b["holding"] or 9), order[b["game_id"]],
                                    int(b["ply"])))
    game_id = best["game_id"]
    in_game = sorted((b for b in real if b["game_id"] == game_id), key=lambda b: int(b["ply"]))
    return ExampleGame(by_id[game_id], in_game, pieces_on_board(best["fen"]), len(pool))
