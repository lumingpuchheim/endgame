"""One example game as an annotated line: a diagram, the moves with marks and comments,
and the final position. Comments come from notes/ or, where there is none, from the engine."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .notes import Note, position_key
from .reader import Move

@dataclass
class Diagram:
    number: int
    fen: str
    label: str = ""


@dataclass
class Shown:
    """Positions already shown in the book: position key -> label of the diagram whose line
    contains it (the diagram itself, or any position reached in the moves after it)."""
    positions: Dict[str, str] = field(default_factory=dict)
    count: int = 0
    labels: set = field(default_factory=set)

    def add(self, fen: str, label: str = "") -> Diagram:
        self.count += 1
        label = label or f"diagram-{self.count}"
        unique, n = label, 2
        while unique in self.labels:
            unique, n = f"{label}-{n}", n + 1
        self.labels.add(unique)
        self.positions.setdefault(position_key(fen), unique)
        return Diagram(self.count, fen, unique)


# Items of a line, in order: ("diagram", Diagram), ("seen", number), ("moves", [(text, bold)]),
# ("note", text), ("end", text)


PIECES = {"K": r"\K", "Q": r"\Q", "R": r"\R", "B": r"\B", "N": r"\N"}   # macros in endgame.sty


def figurine(san: str) -> str:
    """SAN with piece letters as chess figures, for comments in the text (LaTeX, skak fonts)."""
    out = ""
    for i, ch in enumerate(san):
        if ch in PIECES and (i == 0 or san[i - 1] == "="):
            out += PIECES[ch] + ("{}" if i + 1 == len(san) else " ")
        else:
            out += ch
    return out


def _only_pawns(board) -> bool:
    import chess
    return not any(board.pieces(p, c) for p in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
                   for c in (chess.WHITE, chess.BLACK))


def _group(value: Optional[float]) -> str:
    if value is None:
        return ""
    return "winning" if value >= 1.5 else ("losing" if value <= -1.5 else "equal")


def _result_text(result: str, last_eval: Optional[float], pawns_only: bool) -> str:
    """The result, plainly. No guesses about why a game ended."""
    if result not in ("1-0", "0-1", "1/2-1/2"):
        return "No result."
    text = result
    winner = {"winning": "White", "losing": "Black"}.get(_group(last_eval))
    won = {"1-0": "White", "0-1": "Black"}.get(result)
    if winner and winner != won:
        text += f" {winner} failed to convert" + (" in the pawn ending." if pawns_only else ".")
    return text


def build_line(start_fen: str, moves: List[Move], start_ply: int, result: str,
               notes: Dict, shown: Shown, label: str = "") -> List[tuple]:
    """The game from the position before ply `start_ply` to its end."""
    import chess

    board = chess.Board(start_fen)        # the position before the move at start_ply

    items: List[tuple] = []
    key = position_key(board.fen())
    if key in shown.positions:
        return [("seen", shown.positions[key])]
    items.append(("diagram", shown.add(board.fen(), label)))
    start = notes.get((key, "start"))
    if start:
        items.append(("note", start.text))

    diagram = items[-1][1].label
    in_line = {key}                       # this line's positions; added to `shown` at the end
    run: List[tuple] = []
    was_pawns = _only_pawns(board)
    last_eval: Optional[float] = None
    for m in (m for m in moves if m.ply >= start_ply):
        key = position_key(board.fen())
        note: Optional[Note] = notes.get((key, m.san))
        auto = ""
        mark = ""
        if m.blunder and m.blunder.get("best") and m.blunder["best"] != m.san and m.blunder.get("holding") not in ("", "0"):
            mark = "?"
        if note and note.mark:
            mark = note.mark
        run.append((m, mark))
        board.push_san(m.san)
        last_eval = m.eval if m.eval is not None else last_eval
        comment = note.text if note else auto
        pawns_now = _only_pawns(board)
        if pawns_now and not was_pawns:
            comment = (comment + " " if comment else "") + "Now it is a king and pawn ending."
        was_pawns = pawns_now
        now = position_key(board.fen())
        if now in shown.positions and now not in in_line:
            items.append(("moves", run))
            items.append(("seen", shown.positions[now]))
            _remember(shown, in_line, diagram)
            return items
        in_line.add(now)
        if comment:
            items.append(("moves", run))
            items.append(("note", comment))
            run = []
    if run:
        items.append(("moves", run))
    end = notes.get((position_key(board.fen()), "end"))
    items.append(("end", end.text if end else _result_text(result, last_eval, _only_pawns(board))))
    _remember(shown, in_line, diagram)
    return items


def _remember(shown: Shown, keys, diagram: str) -> None:
    for k in keys:
        shown.positions.setdefault(k, diagram)


def plain_text(items) -> str:
    """The line as plain text for the console: '59...a5? 60.Ke2 Kb3 61.Kd2 0-1'."""
    out = []
    for kind, value in items:
        if kind == "moves":
            first = True
            for move, mark in value:
                number = f"{move.number}." if move.white else (f"{move.number}..." if first else "")
                out.append(number + move.san + mark)
                first = False
        elif kind == "seen":
            out.append(f"(already seen: {value})")
        elif kind == "end":
            out.append(value)
    return " ".join(out)
