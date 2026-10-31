"""working.pgn: one PGN per diagram of a book, for the author only (not part of the book).

Each game starts at the diagram position (FEN header) and has the game's moves from there on, so it can
be pasted into the Lichess analysis board. The diagram numbers are LaTeX's; they are read from the
last compiled book (its .aux file) and filled in again after every compile."""

import os
import re
from typing import Dict, List, Optional

NAME = "working.pgn"
_NEWLABEL = re.compile(r"\\newlabel\{([^}]*)\}\{\{(\d+)\}\{(\d+)\}")
_EVENT = re.compile(r'^\[Event "[^"]*"\]\r?\n\[Label "([^"]*)"\]\r?\n\[Game "([^"]*)"\]', re.M)


def movetext(fen: str, sans: List[str]) -> str:
    """'62...Kf4 63.Nd5+ Kf5 ...' from the diagram position."""
    import chess
    board = chess.Board(fen)
    moves = []
    for san in sans:
        try:
            move = board.parse_san(san)
        except ValueError:
            break
        if not move:                    # a null move ("--") ends the line: Lichess cannot read it
            break
        moves.append(move)
        board.push(move)
    return chess.Board(fen).variation_san(moves)


def record(label: str, title: str, fen: str, sans: List[str]) -> dict:
    return {"label": label, "title": title, "fen": fen, "moves": movetext(fen, sans)}


def diagram_numbers(aux_path: str) -> Dict[str, int]:
    """{label: diagram number} from a compiled book's .aux file; {} if there is none yet."""
    if not os.path.exists(aux_path):
        return {}
    with open(aux_path, encoding="utf-8", errors="replace") as handle:
        return {label: int(number) for label, number, _page in _NEWLABEL.findall(handle.read())}


def _event(label: str, numbers: Dict[str, int]) -> str:
    return f"Diagram {numbers[label]}" if label in numbers else f"Diagram {label}"


def text(records: List[dict], numbers: Dict[str, int]) -> str:
    out = []
    for r in records:
        out.append(f'[Event "{_event(r["label"], numbers)}"]\n[Label "{r["label"]}"]\n[Game "{r["title"]}"]\n'
                   f'[SetUp "1"]\n[FEN "{r["fen"]}"]\n\n{r["moves"]} *\n')
    return "\n".join(out)


def write(path: str, records: List[dict], aux_path: Optional[str] = None) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text(records, diagram_numbers(aux_path) if aux_path else {}))


def renumber(path: str, aux_path: str) -> bool:
    """Fill in the diagram numbers of a freshly compiled book. True if the file was there."""
    if not os.path.exists(path):
        return False
    numbers = diagram_numbers(aux_path)
    with open(path, encoding="utf-8") as handle:
        old = handle.read()
    new = _EVENT.sub(lambda m: f'[Event "{_event(m.group(1), numbers)}"]\n[Label "{m.group(1)}"]\n'
                               f'[Game "{m.group(2)}"]', old)
    if new != old:
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(new)
    return True
