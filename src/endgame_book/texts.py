"""Wording used in the book. Everything a reader sees that the program writes is here.

'chapter <<label>>' in a text becomes a clickable cross reference (\\xref{chapter}{label})."""

import datetime
from typing import List, Tuple

from .stats import Row, Summary

PIECE_NAMES = {"Q": "queen", "R": "rook", "B": "bishop", "N": "knight"}
NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight",
                9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}


def _side(side: str) -> str:
    """'RB' -> 'rook and bishop', 'RR' -> 'two rooks', 'pawns' -> 'pawns'."""
    if side == "pawns":
        return "pawns"
    names = []
    for letter in "QRBN":
        count = side.count(letter)
        if count == 1:
            names.append(PIECE_NAMES[letter])
        elif count > 1:
            names.append(f"{NUMBER_WORDS.get(count, count)} {PIECE_NAMES[letter]}s")
    return " and ".join(names)


def material_name(key: str) -> str:
    """'R v R' -> 'Rook vs rook', 'pawns v pawns' -> 'King and pawns', 'R v pawns' -> 'Rook vs pawns'."""
    if key == "B v B same":
        return "Bishop vs bishop, same colour"
    if key == "B v B opposite":
        return "Bishop vs bishop, opposite colours"
    a, _, b = key.partition(" v ")
    if a == b == "pawns":
        return "King and pawns"
    text = f"{_side(a)} vs {_side(b)}"
    return text[0].upper() + text[1:]


def _with_pawns(pieces: str, pawns: int) -> str:
    name = _side(pieces) if pieces else "king"
    if pawns == 0:
        return name
    return f"{name} and " + ("pawn" if pawns == 1 else f"{NUMBER_WORDS.get(pawns, pawns)} pawns")


def pawns_title(split) -> str:
    """Section title from sections.pawn_split: (('R', 2), ('R', 0)) -> 'Rook and two pawns vs rook',
    (('R', 1), ('R', 1)) -> 'Rook and pawn vs rook and pawn'."""
    (pieces_a, pawns_a), (pieces_b, pawns_b) = split
    text = f"{_with_pawns(pieces_a, pawns_a)} vs {_with_pawns(pieces_b, pawns_b)}"
    return text[0].upper() + text[1:]


def players(s: Summary) -> str:
    return f"players rated {s.min_elo} or more" if s.min_elo else "strong players"


# --- Part I ------------------------------------------------------------------

def common_intro(s: Summary) -> List[str]:
    return [
        "Before choosing what to study, it helps to know what you will actually meet over the board. "
        f"This chapter counts, in {s.games:,} games between {players(s)}, how often each endgame came up.",
        "Each bar is one material balance, whoever has which side: “Rook vs rook” counts every "
        "game in which each side had a rook (and pawns). A game that passes through several endgames "
        "counts once for each of them.",
    ]


def common_points(rows: List[Row]) -> List[str]:
    top = rows[:3]
    points = [f"{material_name(top[0].key)} is the endgame you will meet most: it came up in "
              f"{top[0].per_100_games:.0f} of every 100 games."]
    if len(top) > 1:
        rest = ", ".join(f"{material_name(r.key).lower()} ({r.per_100_games:.0f})" for r in top[1:])
        points.append(f"Next come {rest}.")
    return points


def tricky_intro(s: Summary, min_games: int) -> List[str]:
    return [
        "Some endgames are harder than others. This chapter asks: once an endgame is on the board, how "
        "often does a strong player throw away half a point or more?",
        "A blunder here is a move that turns a win into a draw or a loss, or a draw into a loss, while a "
        "better move was available. The bar shows how many such moves were made per 100 games that "
        f"reached the endgame. Endgames that came up in fewer than {min_games:,} games are left out: "
        "with fewer games, chance decides the order.",
    ]


def tricky_points(rows: List[Row]) -> List[str]:
    if not rows:
        return []
    top = rows[0]
    points = [f"{material_name(top.key)} is the hardest to handle: {top.blunders_per_100:.0f} blunders per "
              "100 games that reach it."]
    if len(rows) > 2:
        points.append("Endgames that are hard to play are not always the ones you meet often. "
                      "Chapter <<ch:where-to-start>> puts both together.")
    return points


def overall_intro() -> List[str]:
    return [
        "An endgame deserves your study time if it comes up often and goes wrong often. This chapter "
        "multiplies the two: how many blunders each endgame causes per 100 games played, whether the "
        "game reached that endgame or not.",
        "Read the chart from the top. The endgames there cost strong players the most half points, so "
        "they come first in the rest of the book.",
    ]


def overall_points(rows: List[Row]) -> List[str]:
    if not rows:
        return []
    order = ", then ".join(material_name(r.key).lower() for r in rows[:3])
    first = (f"{material_name(rows[0].key)} alone causes {rows[0].blunders_per_100_all:.0f} blunders per 100 "
             "games played.")
    if rows[0].key == "R v R":
        first += " Part <<part:endgames>> starts there."
    return [f"Study in this order: {order}.", first]


# --- Appendix ----------------------------------------------------------------

def data_lines(s: Summary) -> List[Tuple[str, str]]:
    share = s.games_with_endgame / s.games * 100 if s.games else 0
    if not s.sources:
        files = "-"
    elif len(s.sources) == 1:
        files = s.sources[0]
    else:
        files = f"{s.sources[0]} to {s.sources[-1]} ({len(s.sources)} files)"
    return [
        ("Games", f"{s.games:,} over-the-board games from The Week in Chess"
                  + (f", both players rated {s.min_elo} or more" if s.min_elo else "")),
        ("Source files", files),
        ("Games reaching an endgame", f"{s.games_with_endgame:,} ({share:.0f}%)"),
        ("Endgame rule", s.endgame_rule),
        ("Engine", f"Stockfish, depth {s.depth}"),
        ("Blunders counted", f"{s.real_blunders:,} of {s.marked_blunders:,} marked"),
        ("Numbers made on", datetime.date.today().isoformat()),
    ]


def definitions(min_games: int) -> List[Tuple[str, str]]:
    return [
        ("Endgame", "A position where each side has at most the number of pieces in the endgame rule "
                    "(queens, rooks, bishops, knights; kings and pawns not counted)."),
        ("Material", "The pieces each side has, whoever has which: “Rook and bishop vs rook and "
                     "knight” counts both colours. A game counts once for each material it reaches."),
        ("Exchanges", "A material counts only once it stands for at least 2 moves (one by each side). "
                      "Shorter states in the middle of an exchange belong to the material before them."),
        ("Winning", "At least +1.50 for one side in Stockfish's score; below that the position counts as equal."),
        ("Blunder", "A move after which the mover drops from winning to equal, from equal to losing, or "
                    "from winning to losing, while the engine's best move was a different move and at "
                    "least one move kept the result. Marked moves that fail this test are engine noise "
                    "near the 1.50 line, not mistakes."),
        ("Per 100 games that reach it", "Blunders made in this material, per 100 games that reached it (chapter <<ch:go-wrong>>)."),
        ("Per 100 games played", "Blunders made in this material per 100 games in the data, whether or not "
                                 "they reached it: how often it happens times how often it goes wrong (chapter <<ch:where-to-start>>)."),
        ("Ranking", f"Only materials reached in at least {min_games:,} games are ranked in chapter <<ch:go-wrong>>. "
                    "With fewer games, splitting the data in two halves gave a different top of the list."),
    ]


# --- Part II: one chapter per endgame -------------------------------------------

def chapter_intro(row: Row, rank: int) -> List[str]:
    """Opening paragraphs of an endgame chapter."""
    name = material_name(row.key)
    return [
        f"{name} came up in {row.per_100_games:.1f} of every 100 games. Once it was on the board, strong "
        f"players blundered {row.blunders_per_100:.0f} times per 100 games (chapter <<ch:go-wrong>>). It is "
        f"number {rank} among the endgames of this book in the order of study (chapter <<ch:where-to-start>>).",
        "The positions below are taken from games between grandmasters and other strong players. In each "
        "one, the player to move went wrong. They are ordered from the fewest pawns on the board to the "
        "most, so the first sections hold the cleanest examples.",
        "Before you read the moves, cover them and find the right move yourself. Then read on: the mistake "
        "is marked with ?, and the rest of the game shows what happened. If a game reaches a position you "
        "have already seen, the book says so and stops there.",
    ]
