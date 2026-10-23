"""The rows each section shows, chosen once and used by every output format."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .stats import Row, Summary, is_real_blunder, material


def most_common(s: Summary, top: int) -> List[Row]:
    return sorted(s.by_material, key=lambda r: -r.games)[:top]


def trickiest(s: Summary, min_games: int, top: int) -> List[Row]:
    return sorted([r for r in s.by_material if r.games >= min_games], key=lambda r: -r.blunders_per_100)[:top]


def most_blunders_overall(s: Summary, top: int) -> List[Row]:
    return sorted(s.by_material, key=lambda r: -r.blunders_per_100_all)[:top]


def unranked(s: Summary, min_games: int) -> int:
    return sum(1 for r in s.by_material if r.games < min_games)


def pawn_split(fen: str) -> Tuple[Tuple[str, int], Tuple[str, int]]:
    """((pieces, pawns) of the side with more pawns, (pieces, pawns) of the other side).
    Pieces are letters without king and pawns, e.g. ('R', 2), ('R', 0) for rook and two pawns vs rook."""
    board = fen.split()[0]
    white = ("".join(sorted((c for c in board if c in "QRBN"), key="QRBN".index)), board.count("P"))
    black = ("".join(sorted((c.upper() for c in board if c in "qrbn"), key="QRBN".index)), board.count("p"))
    return (white, black) if white[1] >= black[1] else (black, white)


def pieces_on_board(fen: str) -> int:
    """All pieces on the board, kings and pawns included."""
    return sum(ch.isalpha() for ch in fen.split()[0])


def _imbalance(fen: str) -> int:
    (_, more), (_, fewer) = pawn_split(fen)
    return more - fewer


@dataclass
class Position:
    game: dict
    blunder: dict            # the mistake made in this position
    pieces: int


def positions(games: List[dict], blunders: List[dict], kept_ids: set, wanted: str = "R v R",
              limit: Optional[int] = None) -> Tuple[List[Position], int]:
    """Positions in `wanted` material where a real blunder was made, fewest pieces on the board
    first; same number of pieces: the more lopsided pawns first (R+PP v R before R+P v R+P),
    then input order, then move order. Returns (shown, all found)."""
    by_id: Dict[str, dict] = {g["game_id"]: g for g in games}
    order = {g["game_id"]: i for i, g in enumerate(games)}
    pool = [b for b in blunders if b["game_id"] in kept_ids and is_real_blunder(b) and b["fen"]
            and material(b["signature"]) == wanted]
    pool.sort(key=lambda b: (pieces_on_board(b["fen"]), -_imbalance(b["fen"]), order[b["game_id"]], int(b["ply"])))
    chosen = pool if limit is None else pool[:limit]
    return [Position(by_id[b["game_id"]], b, pieces_on_board(b["fen"])) for b in chosen], len(pool)
