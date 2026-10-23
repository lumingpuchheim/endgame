"""The rows each section shows, chosen once and used by every output format."""

from typing import List

from .stats import Row, Summary


def most_common(s: Summary, top: int) -> List[Row]:
    return sorted(s.by_material, key=lambda r: -r.games)[:top]


def trickiest(s: Summary, min_games: int, top: int) -> List[Row]:
    return sorted([r for r in s.by_material if r.games >= min_games], key=lambda r: -r.blunders_per_100)[:top]


def unranked(s: Summary, min_games: int) -> int:
    return sum(1 for r in s.by_material if r.games < min_games)
