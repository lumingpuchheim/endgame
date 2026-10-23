"""Wording used in the report."""

import datetime
from typing import List, Tuple

from .stats import Summary

TITLE = "Endgames in games between {elo}+ players"
SUBTITLE = "Which endgames occur most often, and in which ones strong players make the most mistakes."


def title(s: Summary) -> str:
    return TITLE.format(elo=s.min_elo) if s.min_elo else "Endgames"


def data_lines(s: Summary) -> List[Tuple[str, str]]:
    share = s.games_with_endgame / s.games * 100 if s.games else 0
    if not s.sources:
        files = "-"
    elif len(s.sources) == 1:
        files = s.sources[0]
    else:
        files = f"{s.sources[0]} to {s.sources[-1]} ({len(s.sources)} files)"
    return [
        ("Source files", files),
        ("Games", f"{s.games:,}" + (f" (both players rated {s.min_elo} or more)" if s.min_elo else "")),
        ("Games reaching an endgame", f"{s.games_with_endgame:,} ({share:.0f}%)"),
        ("Endgame rule", s.endgame_rule),
        ("Engine depth", s.depth),
        ("Blunders counted", f"{s.real_blunders:,} of {s.marked_blunders:,} marked (see definition)"),
        ("Created", datetime.date.today().isoformat()),
    ]


def definitions(min_games: int) -> List[Tuple[str, str]]:
    return [
        ("Endgame", "A position where each side has at most the number of pieces in the endgame rule "
                    "(queens, rooks, bishops, knights; kings and pawns not counted)."),
        ("Material", "The pieces each side has, colour-neutral: 'RB v RN' means rook and bishop against "
                     "rook and knight, whoever has which. A game counts once for each material it reaches."),
        ("Exchanges", "A material counts only once it stands for at least 2 moves (one by each side). "
                      "Shorter states in the middle of an exchange belong to the material before them."),
        ("In N of 100 games", "Out of every 100 games in the data, how many reached this endgame."),
        ("Blunder", "A move after which the mover's position drops a group (winning to equal, equal to "
                    "losing, winning to losing; winning means at least +1.50 for the mover). It counts only "
                    "if the engine's best move was a different move and at least one move kept the group. "
                    "Marked moves that fail this test are engine noise near the 1.50 line, not mistakes."),
        ("Blunders per 100 games", "Blunders made in this material, per 100 games that reached it."),
        ("Blunders per 100 games played", "Blunders made in this material per 100 games in the data, "
                                          "whether or not they reached it. It is how often the material happens "
                                          "times how often it goes wrong."),
        ("Ranking", f"Only materials reached in at least {min_games} games are ranked. With fewer games, "
                    "a handful of games can decide the order: splitting the data in two halves gave a "
                    "different top of the list."),
    ]


SECTIONS = {
    "common": ("1. Most common endgames",
               "How many of every 100 games reach each material. 'pawns' means that side has only king and pawns."),
    "tricky": ("2. Tricky endgames",
               "Blunders per 100 games that reached the material, most first. Only materials reached in at "
               "least {min_games} games are shown."),
    "example": ("4. Rook endings: one game",
                "Rook vs rook causes the most blunders overall (section 3). Of the {candidates:,} rook-ending "
                "blunders in the data, the one with the fewest pieces on the board ({pieces}, kings and pawns "
                "included) happened in this game. The game is shown from that position to the end; earlier, "
                "more complicated mistakes are left out. Diagrams open on "
                "Lichess."),
    "overall": ("3. Endgames with the most blunders overall",
                "Blunders made in each material per 100 games played. This combines sections 1 and 2: a material "
                "comes first if it happens often and goes wrong often. These are the endgames where better "
                "play avoids the most blunders."),
}
