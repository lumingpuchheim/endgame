"""Read annotated PGN files into plain records.

The input format is defined by chessticize-worker's TWIC annotation spec
(docs/input-format.md in this repository). Only headers and comment
commands are used; no engine and no other code from that project.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Iterator, List, Optional

from . import SUPPORTED_ANNOTATORS

logger = logging.getLogger(__name__)

_EVAL = re.compile(r"\[%eval ([^\]\s]+)\]")
_SEGMENT = re.compile(r"\[%eg(start|end) (\S*) (\S+)\]")
_BLUNDER = re.compile(r"\[%blunder (\w+)>(\w+)([^\]]*)\]")
_FEN = re.compile(r"\[%fen ([^\]]+)\]")


def issue_order(path: str) -> list:
    name = os.path.basename(path).lower()
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", name)] + [path]


def find_files(input_dir: str) -> List[str]:
    """All *.annotated.pgn files under input_dir, following links, in issue order."""
    if not os.path.isdir(input_dir):
        raise FileNotFoundError(f"input folder not found: {input_dir}")
    found = []
    for root, _dirs, files in os.walk(input_dir, followlinks=True):
        for name in files:
            if name.lower().endswith(".annotated.pgn"):
                found.append(os.path.join(root, name))
    return sorted(found, key=issue_order)


def parse_eval(text: Optional[str]) -> Optional[float]:
    """Pawns from White's view. Mate scores become +/-100."""
    if not text:
        return None
    if text.startswith("#"):
        return 100.0 if not text.startswith("#-") else -100.0
    try:
        return float(text)
    except ValueError:
        return None


@dataclass
class Segment:
    order: int
    signature: str
    kind: str
    moves: int = 0


@dataclass
class Blunder:
    ply: int
    move_number: int
    segment: int          # index of the material segment the move was played in
    mover: str            # "white" / "black"
    player: str
    signature: str
    kind: str
    group_before: str
    group_after: str
    eval_before: Optional[float]
    eval_after: Optional[float]
    move: str
    best: str
    holding: Optional[int]
    fen: str


@dataclass
class Game:
    source: str
    game_id: str
    event: str
    date: str
    white: str
    black: str
    white_elo: Optional[int]
    black_elo: Optional[int]
    result: str
    time_control: str
    time_control_source: str
    endgame: bool
    start_group: str
    endgame_rule: str
    depth: str
    annotator: str
    segments: List[Segment] = field(default_factory=list)
    blunders: List[Blunder] = field(default_factory=list)


_HEADER = re.compile(r'^\[(\w+) "((?:[^"\\]|\\.)*)"\]\s*$', re.M)
# Movetext tokens: a comment, a move number ("12." or "12..."), a NAG ("$4"), or a move / result.
_TOKEN = re.compile(r"\{([^}]*)\}|(\d+)\.(\.\.)?|(\$\d+)|([^\s{}]+)")
_RESULTS = {"1-0", "0-1", "1/2-1/2", "*"}


def _int(value: str) -> Optional[int]:
    return int(value) if value and value.isdigit() else None


def _blunder_fields(rest: str) -> dict:
    return dict(part.split("=", 1) for part in rest.split() if "=" in part)


def _split_games(text: str) -> Iterator[str]:
    """Each game starts with its [Event ...] header line."""
    starts = [m.start() for m in re.finditer(r"^\[Event ", text, re.M)]
    for i, begin in enumerate(starts):
        yield text[begin: starts[i + 1] if i + 1 < len(starts) else len(text)]


def read_game(text: str, source: str) -> Game:
    """Parse one annotated game from its text. Moves are not replayed: everything the
    report needs is in the headers and the comment commands."""
    head, _, movetext = text.partition("\n\n")
    h = {k: v.replace('\\"', '"') for k, v in _HEADER.findall(head)}
    record = Game(
        source=source, game_id=h.get("GameId", ""), event=h.get("Event", ""), date=h.get("Date", ""),
        white=h.get("White", ""), black=h.get("Black", ""),
        white_elo=_int(h.get("WhiteElo", "")), black_elo=_int(h.get("BlackElo", "")),
        result=h.get("Result", "*"), time_control=h.get("TimeControlClass", ""),
        time_control_source=h.get("TimeControlSource", ""),
        endgame=h.get("EgStartPly", "-") != "-", start_group=h.get("EgStartGroup", "-"),
        endgame_rule=h.get("EndgameRule", ""), depth=h.get("AnnotationDepth", ""),
        annotator=h.get("Annotator", ""),
    )
    if not record.endgame:
        return record

    current: Optional[Segment] = None
    previous_eval: Optional[float] = None
    previous_fen = ""
    move_number, white_to_move = 1, True
    pending = None                         # the last move played, waiting for its comment
    ply = 0

    def finish(move, comment):
        nonlocal current, previous_eval, previous_fen
        number, white_moved, san, move_ply = move
        eval_match = _EVAL.search(comment)
        this_eval = parse_eval(eval_match.group(1)) if eval_match else None
        if current is not None:
            current.moves += 1
            blunder = _BLUNDER.search(comment)
            if blunder:
                extra = _blunder_fields(blunder.group(3))
                record.blunders.append(Blunder(
                    ply=move_ply, move_number=number, segment=current.order,
                    mover="white" if white_moved else "black",
                    player=record.white if white_moved else record.black,
                    signature=current.signature, kind=current.kind,
                    group_before=blunder.group(1), group_after=blunder.group(2),
                    eval_before=previous_eval, eval_after=this_eval, move=san,
                    best=extra.get("best", ""), holding=_int(extra.get("holding", "")), fen=previous_fen,
                ))
        for kind, signature, eg_type in _SEGMENT.findall(comment):
            if kind == "end":
                current = None
            else:
                current = Segment(len(record.segments), signature, eg_type)
                record.segments.append(current)
        if this_eval is not None:
            previous_eval = this_eval
        fen = _FEN.search(comment)
        previous_fen = fen.group(1) if fen else ""

    for m in _TOKEN.finditer(movetext):
        comment, number, dots, nag, word = m.groups()
        if comment is not None:
            if pending:
                finish(pending, comment)
                pending = None
        elif number is not None:
            move_number, white_to_move = int(number), not dots
        elif nag is not None:
            continue
        elif word in _RESULTS:
            break
        else:
            if pending:
                finish(pending, "")
            ply += 1
            pending = (move_number, white_to_move, word, ply)
            if not white_to_move:
                move_number += 1
            white_to_move = not white_to_move
    if pending:
        finish(pending, "")
    return record


def iter_games(path: str) -> Iterator[Game]:
    with open(path, encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    for index, game_text in enumerate(_split_games(text), 1):
        annotator = _header_value(game_text, "Annotator")
        if annotator not in SUPPORTED_ANNOTATORS:
            raise ValueError(f"{path} game {index}: unknown format '{annotator}' "
                             f"(supported: {', '.join(SUPPORTED_ANNOTATORS)})")
        yield read_game(game_text, os.path.basename(path))


def _header_value(text: str, name: str) -> str:
    m = re.search(r'^\[' + name + r' "([^"]*)"\]', text, re.M)
    return m.group(1) if m else ""
