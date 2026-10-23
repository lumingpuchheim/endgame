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


@dataclass
class Shown:
    """Positions already shown in the book: position key -> number of the diagram whose line
    contains it (the diagram itself, or any position reached in the moves after it)."""
    positions: Dict[str, int] = field(default_factory=dict)
    count: int = 0

    def add(self, fen: str) -> Diagram:
        self.count += 1
        self.positions.setdefault(position_key(fen), self.count)
        return Diagram(self.count, fen)


# Items of a line, in order: ("diagram", Diagram), ("seen", number), ("moves", [(text, bold)]),
# ("note", text), ("end", text)


PIECES = {"K": r"\symking", "Q": r"\symqueen", "R": r"\symrook", "B": r"\symbishop", "N": r"\symknight"}


def figurine(san: str) -> str:
    """SAN with piece letters as chess figures, for comments in the text (LaTeX, skak fonts)."""
    out = ""
    for i, ch in enumerate(san):
        if ch in PIECES and (i == 0 or san[i - 1] == "="):
            out += PIECES[ch] + "{}"
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
               notes: Dict, shown: Shown) -> List[tuple]:
    """The game from the position before ply `start_ply` to its end."""
    import chess

    board = chess.Board()
    for m in moves:
        if m.ply >= start_ply:
            break
        board.push_san(m.san)
    if position_key(board.fen()) != position_key(start_fen):
        board = chess.Board(start_fen)     # the game did not start from the initial position

    items: List[tuple] = []
    key = position_key(board.fen())
    if key in shown.positions:
        return [("seen", shown.positions[key])]
    items.append(("diagram", shown.add(board.fen())))
    start = notes.get((key, "start"))
    if start:
        items.append(("note", start.text))

    diagram = shown.count
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


def _remember(shown: Shown, keys, diagram: int) -> None:
    for k in keys:
        shown.positions.setdefault(k, diagram)
