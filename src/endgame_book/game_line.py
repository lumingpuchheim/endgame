"""One example game as an annotated line: a diagram, the moves with marks and comments,
and the final position. Comments come from notes/ or, where there is none, from the engine."""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .notes import NO_MARK, Note, position_key
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
    elsewhere: Dict[str, str] = field(default_factory=dict)   # position key -> label of a diagram in the other book

    def add(self, fen: str, label: str = "") -> Diagram:
        self.count += 1
        label = label or f"diagram-{self.count}"
        unique, n = label, 2
        while unique in self.labels:
            unique, n = f"{label}-{n}", n + 1
        self.labels.add(unique)
        self.positions.setdefault(position_key(fen), unique)
        return Diagram(self.count, fen, unique)

    def register_file(self, path: str) -> None:
        """Take in the diagrams of a chapter file already written (yours or generated), and the
        positions reached in the moves after each, so a new chapter does not show them again."""
        import re
        import chess
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        blocks = re.split(r"(?=\\diagram)", text)
        for block in blocks:
            m = re.match(r"\\diagram(?:\[([^\]]*)\])?\{([^}]*)\}", block)
            if not m:
                continue
            label, fen = m.group(1) or "", m.group(2)
            self.count += 1
            if label:
                self.labels.add(label)
            try:
                board = chess.Board(fen)
            except ValueError:
                continue
            target = label or f"diagram-{self.count}"
            self.positions.setdefault(position_key(board.fen()), target)
            for moves in re.findall(r"\\moves\{([^}]*)\}", block):
                plain = re.sub(r"\\([KQRBN])\s*(\{\})?", r"\1", moves)
                for token in plain.split():
                    san = re.sub(r"^\d+\.(\.\.)?", "", token).rstrip("?!")
                    if not san:
                        continue
                    try:
                        board.push_san(san)
                    except ValueError:
                        break
                    self.positions.setdefault(position_key(board.fen()), target)


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


EXPLAINS_BOTH = "% this comment explains the move before too"   # read by status.py
LONG = 10       # more plies than this without a comment or a mark, before a board: not printed


def shorten(items: List[tuple]) -> List[tuple]:
    """A long stretch of moves without comments or marks that leads to a board (or to a position seen
    before) is not printed: ("skipped", full moves) takes its place, 'After 25 more moves ...'."""
    out = []
    for i, item in enumerate(items):
        nxt = items[i + 1][0] if i + 1 < len(items) else ""
        if (item[0] == "moves" and nxt in ("diagram", "seen") and i > 1 and len(item[1]) > LONG
                and not any(mark for _m, mark in item[1])):
            out.append(("skipped", (len(item[1]) + 1) // 2))
        else:
            out.append(item)
    return out


def build_line(start_fen: str, moves: List[Move], start_ply: int, result: str,
               notes: Dict, shown: Shown, label: str = "") -> List[tuple]:
    """The game from the position before ply `start_ply` to its end."""
    return shorten(_build_line(start_fen, moves, start_ply, result, notes, shown, label))


def _build_line(start_fen: str, moves: List[Move], start_ply: int, result: str,
                notes: Dict, shown: Shown, label: str = "") -> List[tuple]:
    import chess

    board = chess.Board(start_fen)        # the position before the move at start_ply

    items: List[tuple] = []
    key = position_key(board.fen())
    if key in shown.positions:
        return [("seen", shown.positions[key])]
    shown_diagram = shown.add(board.fen(), label)
    items.append(("diagram", shown_diagram))
    start = notes.get((key, "start"))
    if start:
        items.append(("note", start.text))

    diagram = shown_diagram.label
    last_noted, final_eval = _last_note(start_fen, moves, start_ply, notes, shown)
    first_key = key
    previous_mark = ""
    in_line = {key}                       # this line's positions; added to `shown` at the end
    run: List[tuple] = []
    last_eval: Optional[float] = None
    boards_here: set = set()              # positions of the other book shown as a board in this line
    for m in (m for m in moves if m.ply >= start_ply):
        key = position_key(board.fen())
        if key in shown.elsewhere and key not in boards_here and m.ply > start_ply:
            boards_here.add(key)
            # the game reaches a position that is a diagram in the other book: show the board here too
            if run:
                items.append(("moves", run))
                run = []
            items.append(("diagram", shown.add(board.fen(), shown.elsewhere[key])))
        mark_before = previous_mark       # the mark of the move before this one in the line
        note: Optional[Note] = notes.get((key, m.san.rstrip("+#")))     # with or without check sign
        note = note.at(m.number) if note else None
        auto = ""
        mark = ""
        if m.blunder and m.blunder.get("best") and m.blunder["best"] != m.san and m.blunder.get("holding") not in ("", "0"):
            mark = "?"
        if note and note.mark:
            mark = "" if note.mark == NO_MARK else note.mark
        if mark in ("?", "??") and m.ply > start_ply and key not in boards_here and key != first_key:
            # a board before every mistake later in the line, so the reader can stop and think
            boards_here.add(key)
            if run:
                items.append(("moves", run))
                run = []
            side = "w" if m.white else "b"
            here = re.sub(r"-\d+[wb]$", f"-{m.number}{side}", diagram) if re.search(r"-\d+[wb]$", diagram) else ""
            items.append(("diagram", shown.add(board.fen(), here)))
        run.append((m, mark))
        previous_mark = mark
        board.push_san(m.san)
        last_eval = m.eval if m.eval is not None else last_eval
        comment = note.text if note else auto
        now = position_key(board.fen())
        if now in shown.positions and now not in in_line:
            items.append(("moves", run))
            if comment:                    # your note on this move is printed before "seen before"
                items.append(("note", comment))
            items.append(("seen", shown.positions[now]))
            _remember(shown, in_line, diagram)
            return items
        in_line.add(now)
        if comment:
            if mark in ("?", "??") and mark_before in ("?", "??") and (m.blunder or {}).get("before") == "winning":
                # the move before gave this side a win, which this move throws away: the comment that
                # shows the win also shows why the move before was a mistake ("58...Nf3? 59.Kc5? 59.Nd3+! wins")
                comment += "\n" + EXPLAINS_BOTH
            items.append(("moves", run))
            items.append(("note", comment))
            run = []
        if last_noted is not None and m.ply == last_noted and m is not moves[-1] and not notes.get((position_key(board.fen()), "end")):
            # after your last comment the rest of the game is not shown, only its result
            items.append(("end", _rest_text(result, final_eval, _only_pawns(board), moves[-1].number)))
            # the rest of the game still belongs to this diagram: its later mistakes do not come back
            # as diagrams of their own
            rest = board.copy()
            for later in (x for x in moves if x.ply > m.ply):
                rest.push_san(later.san)
                key_later = position_key(rest.fen())
                if key_later in shown.positions and key_later not in in_line:
                    break
                in_line.add(key_later)
            _remember(shown, in_line, diagram)
            return items
    if run:
        items.append(("moves", run))
    end = notes.get((position_key(board.fen()), "end"))
    items.append(("end", end.text if end else _result_text(result, last_eval, _only_pawns(board))))
    _remember(shown, in_line, diagram)
    return items


def _last_note(start_fen: str, moves: List[Move], start_ply: int, notes: Dict, shown: Optional[Shown] = None):
    """(ply of the last game move with a note of yours in this line, or None; the engine's last evaluation of
    the game). The line stops where it reaches a position already shown, so notes after that belong to
    another diagram and do not count."""
    import chess
    board, last, final, stopped = chess.Board(start_fen), None, None, False
    first = position_key(board.fen())
    for m in (m for m in moves if m.ply >= start_ply):
        note = notes.get((position_key(board.fen()), m.san.rstrip("+#")))
        if not stopped and note and note.at(m.number).text:   # a note that only changes the mark prints no comment
            last = m.ply
        board.push_san(m.san)
        now = position_key(board.fen())
        if shown is not None and now != first and now in shown.positions:
            stopped = True
        final = m.eval if m.eval is not None else final
    return last, final


def _rest_text(result: str, last_eval: Optional[float], pawns_only: bool, last_move: int = 0) -> str:
    """The result of a game whose remaining moves are not shown: 'The game was drawn after 105 moves.'"""
    words = {"1-0": "White won", "0-1": "Black won", "1/2-1/2": "The game was drawn"}
    if result not in words:
        return "The rest of the game is not shown."
    text = f"{words[result]} after {last_move} moves." if last_move else f"{words[result]} in the end."
    winner = {"winning": "White", "losing": "Black"}.get(_group(last_eval))
    if winner and winner != {"1-0": "White", "0-1": "Black"}.get(result):
        text += f" {winner} failed to convert" + (" the pawn ending." if pawns_only else ".")
    return text


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
        elif kind == "skipped":
            out.append(f"({value} more moves)")
        elif kind == "end":
            out.append(value)
    return " ".join(out)
