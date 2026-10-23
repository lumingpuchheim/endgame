"""Wording shared by the HTML and LaTeX output, so both say the same thing."""

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
        ("In N of 100 games", "Out of every 100 games in the data, how many reached this endgame."),
        ("Blunder", "A move after which the mover's position drops a group (winning to equal, equal to "
                    "losing, winning to losing; winning means at least +1.50 for the mover). It counts only "
                    "if the engine's best move was a different move and at least one move kept the group. "
                    "Marked moves that fail this test are engine noise near the 1.50 line, not mistakes."),
        ("Blunders per 100 games", "Blunders made in this endgame, per 100 games that reached it, with an "
                                   "approximate 95% range."),
        ("Ranking", f"Only endgames reached in at least {min_games} games are ranked; smaller numbers are "
                    "too noisy to compare."),
    ]


SECTIONS = {
    "common_type": ("1. Most common endgames, by type",
                    "How many of 100 games reach each endgame type. A game can reach several types, so the "
                    "values add up to more than the share of games with an endgame."),
    "common_material": ("1. Most common endgames, by material",
                        "Exact material, colour-neutral. 'pawns' means that side has only king and pawns."),
    "tricky_type": ("2. Tricky endgames, by type",
                    "Blunders per 100 games that reached the endgame type, with an approximate 95% range. "
                    "Types reached in fewer than {min_games} games are left out."),
    "tricky_material": ("2. Tricky endgames, by material",
                        "Materials reached in at least {min_games} games, most blunders per 100 games first. "
                        "'Per 100 games' depends on how long the endgame lasts; 'per 1000 moves' does not."),
}
