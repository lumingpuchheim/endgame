"""What the author wants to see after a build: for each chapter, are all its diagrams commented?

Read from the written chapter files, so it works whether or not make_book rewrote them. A diagram
counts as commented when a comment of yours is printed in its line: a note on the diagram's move,
on a later move, or a 'start'/'end' note. A note that belongs to another diagram does not count: when
a game runs into a position that is a diagram of its own (often in the other book), that diagram's note
is printed there too, but it does not comment on this one."""

import os
import re
from typing import Dict, List, Tuple

_LISTED = re.compile(r"^(?:\\egbook\{(\w+)\}\{)?\\chapterfile\{([^}]*)\}", re.M)
_CHAPTER = re.compile(r"\\chapter\{([^}]*)\}")
_DIAGRAM = re.compile(r"^\\diagram\[([^\]]+)\]")
_END = re.compile(r"^(% note: @|\\section|\\begin\{exercises\})")
_NOT_A_COMMENT = re.compile(r"^(\\moves\{|\\game\{|\\diagram|\\seen\{|\\skipped\{|\\samegame|\\libunit\{|\\yourtext\{|%|"
                            r"(1-0|0-1|1/2-1/2|\*)\\par$|$)")


_KEY = re.compile(r"^% note: @ (\S+ [wb])[^|]*\| (\S+?)[?!]*$")


def _line(text: str) -> str:
    return text.strip()[:-len("\\par")].strip() if text.strip().endswith("\\par") else text.strip()


def mistake_of_line(notes_dir: str = "notes") -> dict:
    """{a line of your notes: (White to move, move number)} for the notes on a mistake (marked ?, ?? or ?!)."""
    from .notes import load_notes
    out = {}
    for (key, move), note in (load_notes(notes_dir) if os.path.isdir(notes_dir) else {}).items():
        for n in [note, *note.again.values()]:
            if move not in ("start", "end", "skip") and "?" in n.mark:
                for line in n.text.split("\n"):
                    if line.strip():
                        out[_line(line)] = (key.split()[1] == "w", n.number)
    return out


def diagram_note_lines(chapters_dir: str, notes_dir: str = "notes") -> dict:
    """{(position, move) of every diagram in the band's chapters: the lines of its note}."""
    from .notes import load_notes
    notes = load_notes(notes_dir) if os.path.isdir(notes_dir) else {}
    keys = set()
    for name in os.listdir(chapters_dir) if os.path.isdir(chapters_dir) else []:
        if name.endswith(".tex"):
            with open(os.path.join(chapters_dir, name), encoding="utf-8") as handle:
                keys |= {(m.group(1), m.group(2).rstrip("+#")) for m in map(_KEY.match, handle) if m}
    return {key: {_line(l) for l in notes[key].text.split("\n") if l.strip()} for key in keys if key in notes}


_MOVES = re.compile(r"^\\moves\{(.*)\}\s*$")
_FIGURE = re.compile(r"\\([KQRBN])\s*(\{\})?")
_BAD = re.compile(r"[^?!](\?\??|\?!)$")     # ?, ?? and ?!, not !?


def _marked_moves(moves: str) -> List[Tuple[str, bool]]:
    """[(move as '56...Bd1?', marked as a mistake), ...] of one \\moves{...} run."""
    out, number = [], ""
    for token in _FIGURE.sub(r"\1", moves).split():
        m = re.match(r"^(\d+\.(?:\.\.)?)(.*)$", token)
        if m:
            number, san = m.group(1), m.group(2)
        else:
            number, san = (re.sub(r"\.$", "...", number) if not number.endswith("...") else number), token
        out.append((number + san, bool(_BAD.search(san))))
    return out


def _join_runs(lines: List[str]) -> List[str]:
    """A board before a mistake splits the moves into two runs; join them again (same number of lines)."""
    out = list(lines)
    for i, line in enumerate(out):
        if not line.strip().startswith("\\diagram"):
            continue
        before = next((j for j in range(i - 1, -1, -1) if out[j].strip()), None)
        after = next((j for j in range(i + 1, len(out)) if out[j].strip()), None)
        if before is None or after is None:
            continue
        a, b = _MOVES.match(out[before].strip()), _MOVES.match(out[after].strip())
        if a and b:
            out[after] = "\\moves{" + a.group(1) + " " + b.group(1) + "}"
            out[before] = ""
    return out


def uncommented_mistakes(lines: List[str], start: int) -> List[str]:
    """Moves marked ? in the \\moves runs of lines[start:] (up to the next diagram's start) that no comment follows."""
    out = []
    lines = _join_runs(lines)
    for i in range(start, len(lines)):
        line = lines[i]
        if i > start and (_END.match(line) or line.startswith(("\\game{", "\\samegame"))):
            break
        m = _MOVES.match(line.strip())
        if not m:
            continue
        moves = _marked_moves(m.group(1))
        after = next((l.strip() for l in lines[i + 1:] if l.strip()), "")
        commented_last = bool(after) and not _NOT_A_COMMENT.match(after)
        covered = {len(moves) - 1} if commented_last else set()     # every mistake needs its own comment
        for n, (move, bad) in enumerate(moves):
            if bad and n not in covered:
                out.append(move)
    return out


_GAME_END = re.compile(r"^(\\game\{|\\samegame|\\section|\\begin\{exercises\}|\\chapter)")


def missed_moves(lines: List[str], details: list = None) -> Dict[str, List[str]]:
    """{board label: warnings} for game moves your lines pass over: a line of yours follows the game
    (83...Rh3 84.Kb5) and then, in a position of the game, gives another move than the game played
    (84.Ra5), and the game's move has neither a mark nor a comment. Diagram 49 of the 1500-1599 book.
    Only the opponent of the side whose mistake the note is about can miss something: after 83...Rh3?,
    White's 84.Ra5 is flagged; Black's own other moves in such a line are just other ways to lose.
    The moves are replayed on a board, so a side line in parentheses starts from its own position,
    not from a game position that merely has the same move number."""
    import chess
    from .notecheck import bare_move, move_name, plain, runs_of_moves
    out: Dict[str, List[str]] = {}
    key = lambda board: " ".join(board.fen().split()[:2])

    def check(start_fen, game, comments):
        if not start_fen or not game:
            return
        try:                            # only a help for the author: it never stops the build
            _check(start_fen, game, comments)
        except Exception:               # noqa: BLE001
            pass

    def _check(start_fen, game, comments):
        board, at = chess.Board(start_fen), {}         # position before each game move: its index
        for i, (n, w, san, _marked, _commented) in enumerate(game):
            at.setdefault(key(board), i)
            try:
                board.push_san(bare_move(san))
            except ValueError:
                game = game[:i]
                break
        at = {k: i for k, i in at.items() if i < len(game)}
        positions = [chess.Board(start_fen)]
        for n, w, san, *_ in game:
            nxt = positions[-1].copy()
            nxt.push_san(bare_move(san))
            positions.append(nxt)
        reported = set()
        for label, text, noted in comments:
            # the side whose mistake the note is about: its other moves in your line are just other
            # ways to lose (Diagram 88: 48...Ke6 instead of 48...e4); only the opponent can miss something
            erring = game[noted][1] if 0 <= noted < len(game) else None
            text = plain(text)
            runs = runs_of_moves(text)
            # moves the comment names itself ("lets Black choose between 65...Kb4 and 65...Kc4",
            # "46.h4? lets the win slip"): the game's move is then commented on
            named = {(n, w, bare_move(san)) for _b, _e, ms in runs for n, w, san in ms}
            starts, ends = [], []      # the board each line starts from and ends on, or None
            in_game = []               # does the line end still following the game
            for r, (begin, _end, moves) in enumerate(runs):
                depth = text[:begin].count("(") - text[:begin].count(")")
                first = (moves[0][0], moves[0][1])
                start, chained, q = None, False, None
                before = (first[0] - 1, False) if first[1] else (first[0], True)    # the move before it
                if depth == 0:
                    # "after 60...Ke6: 61.Ke4 Ke7" goes on from the move just mentioned, not from the game
                    q = next((q for q in range(r - 1, -1, -1)
                              if text[:runs[q][0]].count("(") == text[:runs[q][0]].count(")")), None)
                    chained = q is not None and (runs[q][2][-1][0], runs[q][2][-1][1]) == before
                    if chained:
                        start = ends[q]
                    else:               # otherwise a main line starts from the game: the move with its number
                        i = next((i for i, g in enumerate(game) if (g[0], g[1]) == first), None)
                        start = positions[i] if i is not None else None
                else:                   # a side line: the position in the line it branches off
                    for q in range(r - 1, -1, -1):
                        pbegin, _pe, pmoves = runs[q]
                        pdepth = text[:pbegin].count("(") - text[:pbegin].count(")")
                        if pdepth < depth and starts[q] is not None:
                            board = starts[q].copy()
                            for m in pmoves:
                                if (m[0], m[1]) == first:
                                    start = board
                                    break
                                try:
                                    board = board.copy()
                                    board.push_san(bare_move(m[2]))
                                except ValueError:
                                    break
                            break
                starts.append(start)
                ends.append(None)
                in_game.append(False)
                if start is None:
                    continue
                board = start.copy()
                # a line that goes on from one that followed the game ("After 47...Kd5? White wins:
                # 48.Rf8 ...") follows it too; any other line differs from the game at its first move
                # only as an alternative (Diagram 1: 78...Kd6 79.Kd4), which is no missed move
                followed = depth == 0 and r > 0 and chained and in_game[q]
                for n, w, san in moves:
                    i = at.get(key(board))
                    if i is not None and (game[i][0], game[i][1]) != (n, w):
                        i = None                # the same position by another move order: not the game
                    if i is not None and followed and bare_move(game[i][2]) != bare_move(san):
                        gn, gw, gsan, marked, commented = game[i]
                        if (not marked and not commented and gw != erring and i not in reported
                                and (gn, gw, bare_move(gsan)) not in named):
                            reported.add(i)
                            if details is not None:     # (board, position, game's move, your move)
                                details.append((label, board.fen(), bare_move(gsan), bare_move(san)))
                            out.setdefault(label, []).append(
                                f"the game's {move_name(gn, gw, gsan)} is not the move of your line "
                                f"({move_name(n, w, san)}), but it has no mark and no comment")
                    followed = i is not None and bare_move(game[i][2]) == bare_move(san)
                    try:
                        board.push_san(bare_move(san))
                    except ValueError:
                        break
                else:
                    ends[-1] = board
                    in_game[-1] = followed

    start_fen, game, comments, label = None, [], [], None
    for i, line in enumerate(lines):
        text = line.strip()
        if _GAME_END.match(text):
            check(start_fen, game, comments)
            start_fen, game, comments = None, [], []
            continue
        diagram = re.match(r"^\\diagram\[([^\]]+)\]\{([^}]*)\}", text)
        if diagram:
            label = diagram.group(1)
            if start_fen is None:
                start_fen = diagram.group(2)
            continue
        m = _MOVES.match(text)
        if m:
            moves = _marked_moves(m.group(1))
            after = next((l.strip() for l in lines[i + 1:] if l.strip()), "")
            commented_last = bool(after) and not _NOT_A_COMMENT.match(after) and not _GAME_END.match(after)
            for k, (move, _bad) in enumerate(moves):
                parsed = re.match(r"^(\d+)\.(\.\.)?(.+)$", move)
                if parsed:
                    game.append((int(parsed.group(1)), parsed.group(2) is None, parsed.group(3),
                                 bool(re.search(r"[?!]$", parsed.group(3))),
                                 commented_last and k == len(moves) - 1))
        elif text and not _NOT_A_COMMENT.match(text) and label:
            comments.append((label, _line(text), len(game) - 1))     # the game move it comments on
    check(start_fen, game, comments)
    return out


def chapter_status(path: str, others: dict = None, mistakes: Dict[str, List[str]] = None,
                   lines: Dict[str, List[str]] = None, mistake_of: dict = None) -> Tuple[str, int, List[str]]:
    """(chapter title, diagrams, labels of the diagrams without a comment). others: diagram_note_lines.
    mistakes, if given, gets {label: moves marked ? without a comment} of the commented diagrams;
    lines, if given, gets {label: problems with the lines of moves in your comments} (notecheck.py)."""
    from .notecheck import problems
    checks = lines
    others = others or {}
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().split("\n")
    blocks: List[Tuple[str, List[str]]] = []   # your comments: (board they stand under, lines), one per note
    board = None
    title = next((m.group(1) for m in map(_CHAPTER.search, lines) if m), os.path.basename(path))
    total, missing, label, commented, own = 0, [], None, False, None

    def close():
        if label is not None and not commented:
            missing.append(label)
        elif label is not None and mistakes is not None:
            found = uncommented_mistakes(lines, begin)
            if found:
                mistakes[label] = found
        if checks is not None:
            for where, block in blocks:
                correction = next(((mistake_of or {}).get(l) for l in block if l in (mistake_of or {})), None)
                for problem in problems(" ".join(block), correction):
                    if problem not in checks.get(where, []):
                        checks.setdefault(where, []).append(problem)
        blocks.clear()

    previous, begin = "", 0
    for index, line in enumerate(lines):
        start_of_game = previous.startswith(("\\game{", "\\samegame"))
        previous = line
        any_board = _DIAGRAM.match(line)
        if any_board:
            board = any_board.group(1)
        key = _KEY.match(line)
        if key:
            own = (key.group(1), key.group(2).rstrip("+#"))
        start = _DIAGRAM.match(line) if start_of_game else None   # a board later in a line is not a diagram to comment
        if start or _END.match(line):
            close()
            # a diagram inside one of your notes has your text on the same line
            label, commented = (start.group(1), bool(line[start.end():].split("}", 1)[-1].strip())) \
                if start else (None, False)
            total += bool(start)
            begin = index
        elif label is not None and not _NOT_A_COMMENT.match(line.strip()):
            foreign = any(_line(line) in text for k, text in others.items() if k != own)
            commented = commented or not foreign
            if blocks and blocks[-1][0] == board and blocks[-1][1]:
                blocks[-1][1].append(_line(line))
            else:
                blocks.append((board, [_line(line)]))
        elif label is not None and line.strip() and blocks and blocks[-1][1]:
            blocks.append((board, []))                      # moves or a board: the next comment is another note
    close()
    return title, total, missing


def books_status(chapters_dir: str) -> List[Tuple[str, List[Tuple[str, int, List[str]]]]]:
    """[(book 'one'|'two', [chapter status, ...]), ...] in the order of endgames.tex."""
    listing = os.path.join(chapters_dir, "endgames.tex")
    if not os.path.exists(listing):
        return []
    books: dict = {}
    others = diagram_note_lines(chapters_dir)
    mistake_of = mistake_of_line()
    with open(listing, encoding="utf-8") as handle:
        for book, path in _LISTED.findall(handle.read()):
            if os.path.exists(path):
                found: Dict[str, List[str]] = {}
                checked: Dict[str, List[str]] = {}
                title, total, missing = chapter_status(path, others, found, checked, mistake_of)
                with open(path, encoding="utf-8") as handle:
                    for label, warnings in missed_moves(handle.read().split("\n")).items():
                        checked.setdefault(label, []).extend(warnings)
                books.setdefault(book or "one", []).append((title, total, missing, found, checked))
    return list(books.items())


BOOK_NAMES = {"one": "Book 1: king and pawns, one piece a side", "two": "Book 2: two pieces a side"}


def report(chapters_dir: str, numbers=None, only: str = "") -> str:
    """One line per chapter; diagrams to do by their number in the last compiled book (else their label)."""
    numbers = numbers or {}
    name = lambda label: f"{numbers[label]}" if label in numbers else label
    out = []
    for book, chapters in books_status(chapters_dir):
        if only and book != only:
            continue
        out.append(BOOK_NAMES.get(book, book))
        width = max(len(title) for title, *_rest in chapters)
        for title, total, missing, *_rest in chapters:
            done = total - len(missing)
            mark = "done" if not missing else f"{done}/{total}"
            line = f"  {title:<{width}}  {mark}"
            if missing and done:
                line += "   to do: diagram " + ", ".join(name(m) for m in missing[:6]) + \
                        (f" and {len(missing) - 6} more" if len(missing) > 6 else "")
            elif missing:
                line += "   not started"
            out.append(line)
        out.append("")
        mistakes = [(label, moves) for _t, _n, _m, found, _c in chapters for label, moves in found.items()]
        if mistakes:
            out.append("WARNING moves marked ? without a comment, in diagrams you have annotated:")
            for label, moves in mistakes:
                out.append(f"  diagram {name(label)}: " + ", ".join(moves))
            out.append("")
        unclear = [(label, found) for *_r, checked in chapters for label, found in checked.items()]
        if unclear:
            out.append(f"WARNING lines of moves in your comments, in {len(unclear)} diagrams:")
            for label, found in unclear:
                for problem in found:
                    out.append(f"  diagram {name(label)}: {problem}")
            out.append("")
    return "\n".join(out)
