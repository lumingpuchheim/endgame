"""The typical technical errors of a chapter, counted from the index entries of your notes.

Each commented position counts once for each idea indexed in its note. The position counts as the
attacker's error when the player to move was winning (and threw the win away), otherwise as the
defender's (who had a draw and lost it). The numbers are frequencies: the per cent of the chapter's
commented positions that turn on the idea. Ideas in BROAD are left out: almost every position could
carry them, so they say nothing about what to watch for."""

import re
from collections import Counter
from typing import List, Tuple

from .notes import position_key

BROAD = {
    "Practical play!Process of elimination", "Strategy!Prophylaxis", "Strategy!Do not rush",
    "Practical play!Clear-cut draw", "Strategy!King activity", "Strategy!Active pieces",
    "Practical play!Simple logic", "Practical play!Schematic thinking", "Practical play!Counterplay",
    "Practical play!No easy choice", "Practical play!Only move", "Practical play!Concrete line beats guidelines",
    "Practical play!Long variation, wrong variation", "Strategy!Static advantage",
    "Strategy!Centralize your pieces", "Strategy!Several threats at once", "Strategy!Do not weaken yourself",
    "Strategy!Tying down", "Study-like positions",
}
MAX_BARS = 10

_INDEX = re.compile(r"\\index\{([^}]*)\}")


def label(entry: str) -> str:
    """'Rook!Cut-off' -> 'Cut-off': the chapter already names the ending."""
    text = entry.split("!")[-1]
    return text[0].upper() + text[1:]


def count(entries, notes, general: bool = False, top: int = MAX_BARS) -> List[Tuple[str, float, float]]:
    """(idea, % attacker errors, % defender errors) of the commented positions, most frequent first,
    at most `top`. With general, the broad ideas (BROAD) instead of the technical ones."""
    attacker, defender, commented = tally(entries, notes, general)
    ideas = sorted(set(attacker) | set(defender), key=lambda i: (-(attacker[i] + defender[i]), i))
    share = lambda n: 100.0 * n / commented
    return [(i, share(attacker[i]), share(defender[i])) for i in ideas[:top]]


def tally(entries, notes, general: bool = False):
    """(attacker Counter, defender Counter, commented positions) over the entries."""
    attacker, defender = Counter(), Counter()
    commented = 0
    for pos, _items in entries:
        move = pos.blunder["move"].rstrip("+#")
        note = notes.get((position_key(pos.blunder["fen"]), move))
        if note is None:
            continue
        commented += 1
        ideas = {label(e) for e in _INDEX.findall(note.text) if (e in BROAD) == general}
        side = attacker if pos.blunder.get("group_before") == "winning" else defender
        for idea in ideas:
            side[idea] += 1
    return attacker, defender, commented


def where(chapters, notes, idea: str) -> List[str]:
    """Titles of the chapters where an idea decides positions, most often first (at most three)."""
    counts = []
    for title, entries in chapters:
        a, d, _n = tally(entries, notes)
        if a[idea] + d[idea]:
            counts.append((-(a[idea] + d[idea]), title))
    return [title for _c, title in sorted(counts)[:3]]
