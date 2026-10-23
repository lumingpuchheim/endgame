"""One example game as an annotated line: a diagram, the moves with marks and comments,
and the final position. Comments come from notes/ or, where there is none, from the engine."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .notes import Note, position_key
from .reader import Move

VERB = {"winning": "wins", "equal": "draws", "losing": "loses"}


@dataclass
class Diagram:
    number: int
    fen: str


@dataclass
class Shown:
    """Positions already shown as diagrams in the report: position key -> diagram number."""
    positions: Dict[str, int] = field(default_factory=dict)
    count: int = 0

    def add(self, fen: str) -> Diagram:
        self.count += 1
        self.positions.setdefault(position_key(fen), self.count)
        return Diagram(self.count, fen)


# Items of a line, in order: ("diagram", Diagram), ("seen", number), ("moves", [(text, bold)]),
# ("note", text), ("end", text)


def move_text(move: Move, mark: str = "", first: bool = False) -> str:
    if move.white:
        return f"{move.number}.{move.san}{mark}"
    return (f"{move.number}...{move.san}{mark}" if first else f"{move.san}{mark}")


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
        return "The score ends here without a result."
    text = f"The score ends here: {result}."
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

    run: List[str] = []
    first = True
    was_pawns = _only_pawns(board)
    last_eval: Optional[float] = None
    for m in (m for m in moves if m.ply >= start_ply):
        key = position_key(board.fen())
        note: Optional[Note] = notes.get((key, m.san))
        auto = ""
        mark = ""
        if m.blunder and m.blunder.get("best") and m.blunder["best"] != m.san and m.blunder.get("holding") not in ("", "0"):
            mark = "?"
            best = Move(m.ply, m.number, m.white, m.blunder["best"], None, {})
            auto = f"{move_text(best, '!', first=True)} {VERB.get(m.blunder['before'], '')}.".replace(" .", ".")
        if note and note.mark:
            mark = note.mark
        run.append(move_text(m, mark, first))
        first = False
        board.push_san(m.san)
        last_eval = m.eval if m.eval is not None else last_eval
        comment = note.text if note else auto
        pawns_now = _only_pawns(board)
        if pawns_now and not was_pawns:
            comment = (comment + " " if comment else "") + "Now it is a king and pawn ending."
        was_pawns = pawns_now
        if position_key(board.fen()) in shown.positions and board.ply() > 0 and run:
            items.append(("moves", run))
            items.append(("seen", shown.positions[position_key(board.fen())]))
            return items
        if comment:
            items.append(("moves", run))
            items.append(("note", comment))
            run, first = [], True
    if run:
        items.append(("moves", run))
    end_key = position_key(board.fen())
    if end_key in shown.positions:
        items.append(("seen", shown.positions[end_key]))
    else:
        items.append(("diagram", shown.add(board.fen())))
    end = notes.get((end_key, "end"))
    items.append(("end", end.text if end else _result_text(result, last_eval, _only_pawns(board))))
    return items
