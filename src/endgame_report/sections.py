"""The rows each section shows, chosen once and used by every output format."""

from typing import List

from .stats import Row, Summary


def common_categories(s: Summary) -> List[Row]:
    return sorted(s.by_category, key=lambda r: -r.per_100_games)


def common_materials(s: Summary, top: int) -> List[Row]:
    return sorted(s.by_material, key=lambda r: -r.games)[:top]


def tricky_categories(s: Summary, min_games: int) -> List[Row]:
    return sorted([r for r in s.by_category if r.games >= min_games], key=lambda r: -r.blunders_per_100)


def tricky_materials(s: Summary, min_games: int, top: int) -> List[Row]:
    return sorted([r for r in s.by_material if r.games >= min_games], key=lambda r: -r.blunders_per_100)[:top]


def unranked(rows: List[Row], min_games: int) -> int:
    return sum(1 for r in rows if r.games < min_games)
