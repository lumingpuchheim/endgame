"""The rows each section shows, chosen once and used by every output format."""

from typing import List

from .stats import Row, Summary


def common_types(s: Summary) -> List[Row]:
    return sorted(s.by_type, key=lambda r: -r.per_100_games)


def common_materials(s: Summary, top: int) -> List[Row]:
    return sorted(s.by_signature, key=lambda r: -r.games)[:top]


def tricky_types(s: Summary, min_games: int) -> List[Row]:
    return sorted([r for r in s.by_type if r.games >= min_games], key=lambda r: -r.blunders_per_100)


def tricky_materials(s: Summary, min_games: int, top: int) -> List[Row]:
    return sorted([r for r in s.by_signature if r.games >= min_games], key=lambda r: -r.blunders_per_100)[:top]


def unranked_materials(s: Summary, min_games: int) -> int:
    return sum(1 for r in s.by_signature if r.games < min_games)
