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
    Pieces are letters without king and pawns, e.g. ('R', 2), ('R', 0) for rook and two pawns vs rook.
    With as many pawns on both sides, the colours do not matter: the side with the stronger pieces
    (queen, rook, bishop, knight in that order) comes first, so 'rook and bishop and two pawns vs rook
    and knight and two pawns' is one section whoever has the bishop."""
    board = fen.split()[0]
    white = ("".join(sorted((c for c in board if c in "QRBN"), key="QRBN".index)), board.count("P"))
    black = ("".join(sorted((c.upper() for c in board if c in "qrbn"), key="QRBN".index)), board.count("p"))
    return _split(white, black)


def _split(white, black):
    if white[1] == black[1]:
        strength = lambda side: [("QRBN".index(c)) for c in side[0]] + [9]
        return tuple(sorted((white, black), key=strength))
    return (white, black) if white[1] > black[1] else (black, white)


MANY = ("many",)      # the section for all positions where one side has MANY_PAWNS pawns or more
MANY_PAWNS = 3


def section_of(fen: str):
    """The chapter section of a position: its pawn balance, or MANY when one side has three or
    more pawns (those are not worth a section each)."""
    split = pawn_split(fen)
    return MANY if split[0][1] >= MANY_PAWNS else split


def _section_order(section) -> tuple:
    return () if section == MANY else section


def section_sort_key(section) -> tuple:
    """The order of the sections in a chapter, the same as the order of the positions in it."""
    if section == MANY:
        return (True,)
    (pieces_a, pawns_a), (pieces_b, pawns_b) = section
    return (False, 2 + len(pieces_a) + pawns_a + len(pieces_b) + pawns_b, pawns_a - pawns_b, section)


def possible_sections(key: str) -> list:
    """Every section a chapter can have: each pawn balance up to MANY_PAWNS - 1 pawns a side, and MANY.
    key: the chapter's material, e.g. 'R v R', 'B v N', 'pawns v pawns', 'B v B opposite'."""
    if key.startswith("B v B "):
        sides = ["B", "B"]
    else:
        sides = ["" if side == "pawns" else side for side in key.split(" v ")]
    if len(sides) != 2:
        return [MANY]
    order = lambda side: "".join(sorted(side, key="QRBN".index))
    a, b = order(sides[0]), order(sides[1])
    found = []
    for pawns_a in range(MANY_PAWNS):
        for pawns_b in range(MANY_PAWNS):
            if a == b == "" and pawns_a == pawns_b == 0:
                continue
            split = _split((a, pawns_a), (b, pawns_b))
            if split not in found:
                found.append(split)
    return found + [MANY]


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
    first; same number of pieces: the more even pawns first (N+P v N+P before N+2P v N),
    then input order, then move order. Returns (shown, all found)."""
    by_id: Dict[str, dict] = {g["game_id"]: g for g in games}
    order = {g["game_id"]: i for i, g in enumerate(games)}
    pool = [b for b in blunders if b["game_id"] in kept_ids and is_real_blunder(b) and b["fen"]
            and material(b["signature"], b.get("kind", "")) == wanted]
    # The section itself is part of the key: with different pieces on the two sides (bishop vs knight),
    # "bishop and pawn vs knight and pawn" and "knight and pawn vs bishop and pawn" would otherwise
    # mix, and each change between them would start a new section with the same title as before.
    pool.sort(key=lambda b: (section_of(b["fen"]) == MANY, pieces_on_board(b["fen"]), _imbalance(b["fen"]),
                             _section_order(section_of(b["fen"])), order[b["game_id"]], int(b["ply"])))
    chosen = pool if limit is None else pool[:limit]
    return [Position(by_id[b["game_id"]], b, pieces_on_board(b["fen"])) for b in chosen], len(pool)
