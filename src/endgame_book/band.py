"""An Elo band: which games a book is about, and the names that follow from it."""

import os
from dataclasses import dataclass
from typing import Optional

RULES = ("both", "average")
BOOKS = "books"


@dataclass(frozen=True)
class Band:
    min_elo: Optional[int] = None
    max_elo: Optional[int] = None
    rule: str = "both"            # "both" players within the limits, or their "average"

    def ok(self, game: dict) -> bool:
        if self.min_elo is None and self.max_elo is None:
            return True
        w, b = str(game.get("white_elo", "")), str(game.get("black_elo", ""))
        if not (w.isdigit() and b.isdigit()):
            return False
        values = [int(w), int(b)] if self.rule == "both" else [(int(w) + int(b)) / 2]
        return all((self.min_elo is None or v >= self.min_elo) and (self.max_elo is None or v <= self.max_elo)
                   for v in values)

    @property
    def slug(self) -> str:
        """'1500-1599-average', '2600-plus-both', 'upto-1599-average', 'all'."""
        if self.min_elo is None and self.max_elo is None:
            return "all"
        if self.max_elo is None:
            span = f"{self.min_elo}-plus"
        elif self.min_elo is None:
            span = f"upto-{self.max_elo}"
        else:
            span = f"{self.min_elo}-{self.max_elo}"
        return f"{span}-{self.rule}"

    def describe(self, latex: bool = False) -> str:
        """'Rated 1500-1599 (average of both players)' for covers and the first page."""
        dash = "--" if latex else "–"
        if self.min_elo is None and self.max_elo is None:
            return "All ratings"
        if self.max_elo is None:
            span = f"Rated {self.min_elo} and above"
        elif self.min_elo is None:
            span = f"Rated {self.max_elo} and below"
        else:
            span = f"Rated {self.min_elo}{dash}{self.max_elo}"
        return span + (" (both players)" if self.rule == "both" else " (average of both players)")

    @property
    def folder(self) -> str:
        return os.path.join(BOOKS, self.slug)

    @property
    def chapters(self) -> str:
        return os.path.join(self.folder, "chapters")

    @property
    def job(self) -> str:
        """Name of the PDF without .pdf: Endgames-Elo-1500-1599-average."""
        return f"Endgames-Elo-{self.slug}"
