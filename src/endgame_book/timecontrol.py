"""Classical or fast (rapid, blitz)? And the choice of positions by time control (make_book --time-control).

The game files rarely say how fast a game was, so the event name decides: 'Blitz', 'Rapid',
'Armageddon' and similar words mean a fast game. Events whose names do not say so go into
notes/fast-events.txt, one name (or part of a name) per line."""

import os
import re
from typing import List

CHOICES = ("all", "mixed", "classical", "fast")
_FAST = re.compile(r"blitz|rapid|armageddon|bullet|speed|lightning|fischer ?random|960", re.I)
FAST_EVENTS = os.path.join("notes", "fast-events.txt")


def _fast_events(path: str = FAST_EVENTS) -> List[str]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as handle:
        return [l.strip().lower() for l in handle if l.strip() and not l.lstrip().startswith("#")]


def is_fast(game: dict, events: List[str] = None) -> bool:
    tc = str(game.get("time_control", "")).lower()
    if tc in ("blitz", "rapid", "bullet"):
        return True
    if tc in ("classical", "standard"):
        return False
    event = str(game.get("event", ""))
    events = _fast_events() if events is None else events
    return bool(_FAST.search(event)) or any(e in event.lower() for e in events)


def kind(position) -> str:
    """'fast' or 'classical', for the half-and-half rule of --time-control mixed."""
    global _EVENTS
    if _EVENTS is None:
        _EVENTS = _fast_events()
    return "fast" if is_fast(position.game, _EVENTS) else "classical"


_EVENTS = None


def choose(positions: list, how: str = "all") -> list:
    """The candidate positions for a chapter, in their order: all of them, only classical or only fast
    games, or mixed: classical and fast taken in turn, so that a chapter gets about half of each."""
    if how == "all":
        return list(positions)
    events = _fast_events()
    fast = [p for p in positions if is_fast(p.game, events)]
    classical = [p for p in positions if not is_fast(p.game, events)]
    if how == "classical":
        return classical
    if how == "fast":
        return fast
    mixed = []
    for i in range(max(len(fast), len(classical))):
        mixed += classical[i:i + 1] + fast[i:i + 1]
    return mixed
