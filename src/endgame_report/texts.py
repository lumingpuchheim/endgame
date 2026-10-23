"""Wording used in the report."""

import datetime
from typing import List, Tuple

from .stats import Summary

def subtitle(s: Summary) -> str:
    players = f"players rated {s.min_elo} or more" if s.min_elo else "strong players"
    return f"An endgame book built from {s.games:,} games between {players}"


def introduction(s: Summary) -> List[str]:
    """Paragraphs: the logic of the book."""
    players = f"players rated {s.min_elo} or more" if s.min_elo else "the players in the data"
    return [
        "This book follows one idea. Study time is limited, so spend it where it pays most: find the "
        "endgames in which strong players make the most mistakes, and correct those first.",
        f"Stockfish checked every endgame in {s.games:,} over-the-board games between {players} and "
        "marked each move that threw away a win or a draw. Chapter 1 shows which endgames happen most "
        "often. Chapter 2 shows which ones go wrong most often once they happen. Chapter 3 puts the two "
        "together: the endgames at the top of it cause the most mistakes in all, so they come first.",
        "The chapters after that take these endgames in this order. Each starts from the simplest "
        "position in which a strong player went wrong and moves on to more complex ones.",
    ]


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
    "overall": ("3. Endgames with the most blunders overall",
                "Blunders made in each material per 100 games played. This combines sections 1 and 2: a material "
                "comes first if it happens often and goes wrong often. These are the endgames where better "
                "play avoids the most blunders."),
}
