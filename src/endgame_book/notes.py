"""Hand-written comments from the notes/ folder (format: notes/README.md)."""

import os
from dataclasses import dataclass
from typing import Dict, Tuple

MARKS = ("!!", "??", "!?", "?!", "!", "?")
NO_MARK = "(no mark)"     # "@ <FEN> | Kh6 (no mark)": the move is printed without a mark


def position_key(fen: str) -> str:
    """Board and side to move: two positions are the same if these are."""
    parts = fen.split()
    return f"{parts[0]} {parts[1] if len(parts) > 1 else 'w'}"


def split_mark(move: str) -> Tuple[str, str]:
    if move.endswith(NO_MARK):
        return move[: -len(NO_MARK)].strip(), NO_MARK
    for mark in MARKS:
        if move.endswith(mark):
            return move[: -len(mark)], mark
    return move, ""


@dataclass
class Note:
    mark: str
    text: str


def paragraphs(lines) -> str:
    """The comment's lines: one paragraph each, separated by blank lines, as in LaTeX."""
    paras, current = [], []
    for line in lines:
        if line.strip():
            current.append(line.strip())
        elif current:
            paras.append(" ".join(current))
            current = []
    if current:
        paras.append(" ".join(current))
    return "\n\n".join(paras)


def load_notes(folder: str) -> Dict[Tuple[str, str], Note]:
    """{(position key, move without mark or 'start'/'end'): Note}."""
    notes: Dict[Tuple[str, str], Note] = {}
    if not os.path.isdir(folder):
        return notes
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".tex"):
            continue
        key, lines = None, []

        def flush():
            if key is not None:
                notes[key[0]] = Note(key[1], paragraphs(lines))

        with open(os.path.join(folder, name), encoding="utf-8") as handle:
            for line in handle:
                if line.lstrip().startswith("%"):
                    continue
                if line.startswith("@"):
                    flush()
                    fen, _, move = line[1:].partition("|")
                    san, mark = split_mark(move.strip())
                    san = san.rstrip("+#")      # g3 and g3+ are the same move
                    if not fen.strip() or not san:
                        raise ValueError(f"{name}: bad note line: {line.strip()}")
                    key, lines = ((position_key(fen.strip()), san), mark), []
                else:
                    lines.append(line)
        flush()
    return notes
