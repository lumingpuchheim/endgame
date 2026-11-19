"""Books of whole games with your own comments, e.g. "Grandmaster Plays" (chapter 6 of myChessNotebook).

    python -m endgame_book.gamebook grandmaster-plays      (or scripts\\make_games.bat grandmaster-plays)

A book is a folder games/<book>/ with
- games.txt      the games in order, one name per line;
- <name>.pgn     the game's moves (from the PGN the game is played through, so the moves are always legal);
- <name>.tex     your comments: a line "@ <move>" (e.g. "@ 7...d6", "@ 24.Qb5 | board") and below it the
                 text that follows that move; "@ title | <heading>" for the game's heading, "@ end" for
                 text after the last move. Write variations as in the endgame notes: 7...O-O 8.c5, pieces
                 as \\K \\Q \\R \\B \\N, side lines in parentheses;
- intro.tex      the chapter's introduction (optional); title.tex: \\newcommand{\\gbtitle}{...} (optional).

The builder plays every game and every variation in your comments on a board and reports each move that
cannot be played, with the line it is in, before anything is compiled. Boards are drawn once by the board
cache (output/boards). Library units (lib/, \\uses{name}, \\term{name}) are put before the first game
that uses them, as in the endgame books. The PDF is books/<book>/<Book>.pdf."""

import argparse
import os
import re
import shutil
import sys
from typing import Dict, List, Optional, Tuple

import chess
import chess.pgn

from . import boards, compile as tex, library
from .notecheck import plain, runs_of_moves, bare_move

GAMES = "games"
NAG = {1: "!", 2: "?", 3: "!!", 4: "??", 5: "!?", 6: "?!"}
FIGURE = {"K": "\\K ", "Q": "\\Q ", "R": "\\R ", "B": "\\B ", "N": "\\N "}


class Note:
    def __init__(self, label: str, board: bool):
        self.label, self.board, self.lines = label, board, []

    @property
    def text(self) -> str:
        return "\n".join(self.lines).strip()


def read_notes(path: str) -> Tuple[str, List[Note]]:
    """(title, notes in file order) from a game's .tex file."""
    title, notes, current = "", [], None
    if not os.path.exists(path):
        return title, notes
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if line.startswith("@"):
                head, _, option = line[1:].partition("|")
                head, option = head.strip(), option.strip()
                if head == "title":
                    title, current = option, None
                    continue
                current = Note(head, option == "board")
                notes.append(current)
            elif current is not None and not line.lstrip().startswith("%"):
                current.lines.append(line)
    return title, notes


def label_of(board: chess.Board, move: chess.Move) -> str:
    return f"{board.fullmove_number}{'.' if board.turn else '...'}{board.san(move)}"


def key(label: str) -> str:
    """'24...Rfxf4?' and '24...Rfxf4' are the same move."""
    return re.sub(r"[?!+#]+$", "", label.replace(" ", ""))


def figurines(san: str) -> str:
    return FIGURE[san[0]] + san[1:] if san[0] in FIGURE else san


# ---------------------------------------------------------------------------------------------
# Checking the moves of your comments
# ---------------------------------------------------------------------------------------------

def check_comment(text: str, before: Dict[Tuple[int, bool], chess.Board],
                  here: Optional[chess.Board] = None) -> List[str]:
    """The moves in a comment that cannot be played. Each line starts from the game's position before the
    move with its number (an alternative to the game's move), or goes on from the line just before it
    ("10...Kh8. 11.c5+ Be6"), also as a plan that skips the opponent's reply ("threatens 33.Rxb4 and
    then 34.Qb7"), or, in parentheses, branches off the line it stands in; a board of its own in the
    comment (\\diagram{FEN}) is a starting position too."""
    text = plain(text)
    runs = runs_of_moves(text)
    own = [chess.Board(m.group(1)) for m in re.finditer(r"\\diagram(?:\[[^\]]*\])?\{([^}]*)\}", text)
           if _fen_ok(m.group(1))]
    ends: List[Optional[chess.Board]] = []
    starts: List[Optional[chess.Board]] = []
    problems = []
    for r, (begin, _end, moves) in enumerate(runs):
        depth = text[:begin].count("(") - text[:begin].count(")")
        first = (moves[0][0], moves[0][1])
        candidates: List[chess.Board] = []
        for q in range(r - 1, -1, -1):                  # the line just before, or the one it branches off
            qdepth = text[:runs[q][0]].count("(") - text[:runs[q][0]].count(")")
            if starts[q] is None:
                continue
            board = starts[q].copy()
            for n, w, san in runs[q][2]:
                if (n, w) == first:
                    candidates.append(board.copy())
                try:
                    board.push_san(bare_move(san))
                except ValueError:
                    break
            if (board.fullmove_number, board.turn) == first:
                candidates.append(board.copy())
            # a plan or a threat: "threatens 33.Rxb4 and then 34.Qb7" skips the opponent's reply
            if not board.is_check():
                skipped = board.copy()
                skipped.push(chess.Move.null())
                if (skipped.fullmove_number, skipped.turn) == first:
                    candidates.append(skipped)
            if qdepth <= depth:
                break
        if first in before:
            candidates.append(before[first].copy())
        # a threat from the position of the note ("Black threatens 26...Qd1" after 25...Qd7): the side to
        # move passes, the game's next move is not played
        if here is not None and not here.is_check():
            passed = here.copy()
            passed.push(chess.Move.null())
            if (passed.fullmove_number, passed.turn) == first:
                candidates.append(passed)
        candidates += [b.copy() for b in own if (b.fullmove_number, b.turn) == first]
        best, best_done, chosen = None, -1, None
        for start in candidates:
            board, done = start.copy(), 0
            for n, w, san in moves:
                try:
                    board.push_san(bare_move(san))
                    done += 1
                except ValueError:
                    break
            if done == len(moves):
                chosen = (start, board)
                break
            if done > best_done:
                best, best_done = start, done
        if chosen:
            starts.append(chosen[0])
            ends.append(chosen[1])
            continue
        starts.append(None)
        ends.append(None)
        line = _shown(moves)
        if not candidates:
            problems.append(f"{line}: no position to start from (move {_name(*moves[0])} is not in the game)")
        else:
            bad = moves[best_done]
            problems.append(f"{line}: {_name(*bad)} cannot be played")
    return problems


def _fen_ok(fen: str) -> bool:
    try:
        chess.Board(fen)
        return True
    except ValueError:
        return False


def _name(n: int, w: bool, san: str) -> str:
    return f"{n}{'.' if w else '...'}{san}"


def _shown(moves) -> str:
    return _name(*moves[0]) if len(moves) == 1 else f"{_name(*moves[0])} ... {_name(*moves[-1])}"


# ---------------------------------------------------------------------------------------------
# Writing the chapter
# ---------------------------------------------------------------------------------------------

def game_latex(name: str, folder: str, report: List[str]) -> str:
    """One game as LaTeX: heading, the moves with your comments between them, boards where you asked."""
    with open(os.path.join(folder, name + ".pgn"), encoding="utf-8") as handle:
        game = chess.pgn.read_game(handle)
    title, notes = read_notes(os.path.join(folder, name + ".tex"))
    h = game.headers
    title = title or f"{h.get('White', '?')} - {h.get('Black', '?')}, {h.get('Event', '')} {h.get('Date', '')[:4]}"
    by_move: Dict[str, Note] = {}
    end_note: Optional[Note] = None
    for note in notes:
        if note.label in ("end", "start"):
            end_note = note if note.label == "end" else end_note
            continue
        by_move[key(note.label)] = note

    out = [f"% note: @ {name}", f"\\section{{{_tex_title(title)}}}",
           f"{{\\color{{muted}}{h.get('Event', '')} {h.get('Date', '')[:4]}, {h.get('Result', '')}}}\\par", ""]
    start_note = next((n for n in notes if n.label == "start"), None)
    if start_note and start_note.text:
        out += [start_note.text, ""]
    before: Dict[Tuple[int, bool], chess.Board] = {}      # every position of the game, before each move
    board = game.board()
    for move in game.mainline_moves():
        before[(board.fullmove_number, board.turn)] = board.copy()
        board.push(move)
    before[(board.fullmove_number, board.turn)] = board.copy()   # after the last move
    board = game.board()
    run: List[str] = []
    resume = True                                   # write the move number of a black move after a break
    found = set()
    for node in game.mainline():
        move = node.move
        label = label_of(board, move)
        number = (f"{board.fullmove_number}." if board.turn
                  else (f"{board.fullmove_number}..." if resume else ""))
        mark = "".join(NAG.get(n, "") for n in sorted(node.nags))
        run.append(number + figurines(board.san(move)) + mark)
        resume = False
        board.push(move)
        note = by_move.get(key(label))
        if note is None:
            continue
        found.add(key(label))
        out.append("\\moves{" + " ".join(run) + "}")
        run, resume = [], True
        out.append(f"% note: @ {name} {label}")
        if note.board:
            out.append(f"\\diagram[{name}-{_slug(label)}]{{{board.fen()}}}")
        if note.text:
            out += [note.text, ""]
        for problem in check_comment(note.text, before, board):
            report.append(f"{name}, {label}: {problem}")
    if run:
        out.append("\\moves{" + " ".join(run) + "}")
    out.append(f"\\textbf{{{h.get('Result', '')}}}\\par")
    for label in by_move:
        if label not in found:
            report.append(f"{name}: @ {by_move[label].label} is not a move of the game")
    if end_note and end_note.text:
        out += ["", f"% note: @ {name} end", end_note.text]
        for problem in check_comment(end_note.text, before):
            report.append(f"{name}, end: {problem}")
    return "\n".join(out) + "\n"


def _slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


def _tex_title(title: str) -> str:
    return title.replace(" - ", " -- ")


def chapter_latex(book: str, folder: str, report: List[str]) -> str:
    names = [l.strip() for l in open(os.path.join(folder, "games.txt"), encoding="utf-8")
             if l.strip() and not l.startswith("#")]
    title = _book_title(folder, book)
    parts = [f"\\chapter{{{title}}}\\label{{ch:{book}}}"]
    intro = os.path.join(folder, "intro.tex")
    if os.path.exists(intro):
        parts.append(open(intro, encoding="utf-8").read())
    for name in names:
        parts.append(game_latex(name, folder, report))
    body = "\n".join(parts)
    return library.link(body, library.units(), set(), ())


def _book_title(folder: str, book: str) -> str:
    path = os.path.join(folder, "title.tex")
    if os.path.exists(path):
        m = re.search(r"\\newcommand\{\\gbtitle\}\{([^}]*)\}", open(path, encoding="utf-8").read())
        if m:
            return m.group(1)
    return book.replace("-", " ").title()


MAIN = r"""\documentclass[11pt,a4paper,oneside]{memoir}
\usepackage{endgame}
% Your two voices, as in myChessNotebook: what you thought at the board, and what you saw afterwards.
\providecommand{\mythoughts}[1]{{\itshape #1}}
\providecommand{\myreflection}[1]{{\color{teal}#1}}
\providecommand{\engine}[1]{\texttt{#1}}
\hypersetup{pdftitle={@@TITLE@@}, pdfauthor={Ming Lu}}
\begin{document}
\frontmatter
\begin{titlingpage}\centering\vspace*{5cm}{\Huge\bfseries\color{ocre}@@TITLE@@\par}\vspace{1cm}
{\Large Ming Lu\par}\end{titlingpage}
\tableofcontents*
\mainmatter
\input{@@CHAPTER@@}
\backmatter
\printglossary[title={Glossary}]
\printindex
\end{document}
"""


def build(book: str, compile_pdf: bool = True) -> int:
    folder = os.path.join(GAMES, book)
    out_folder = os.path.join("books", book)
    chapters = os.path.join(out_folder, "chapters")
    os.makedirs(chapters, exist_ok=True)
    report: List[str] = []
    chapter = chapter_latex(book, folder, report)
    chapter_path = os.path.join(chapters, book + ".tex")
    with open(chapter_path, "w", encoding="utf-8") as handle:
        handle.write(f"% Written by the game book builder from games/{book}. Do not edit: your comments are in "
                     f"games/{book}/<game>.tex.\n" + chapter)
    print(f"written   {chapter_path}")
    if report:
        print(f"\n{len(report)} moves in your comments cannot be played:")
        for line in report:
            print("  " + line)
        print()
    else:
        print("All moves in your comments can be played.")
    if not compile_pdf:
        return 0
    pdflatex = shutil.which("pdflatex")
    if not pdflatex:
        print("pdflatex was not found. Install MiKTeX: https://miktex.org/download")
        return 1
    new, total = boards.update(files=[chapter_path] + boards.tex_files(("lib",)), pdflatex=pdflatex)
    print(f"boards    {total} ({new} new)")
    title = _book_title(folder, book)
    job = title.replace(" ", "-")
    main = os.path.join(out_folder, "main.tex")
    with open(main, "w", encoding="utf-8") as handle:
        handle.write(MAIN.replace("@@TITLE@@", title).replace("@@CHAPTER@@", chapter_path.replace(os.sep, "/")))
    tex.OUT = os.path.join(out_folder, "build")
    os.makedirs(tex.OUT, exist_ok=True)
    for number in range(1, tex.MAX_PASSES + 1):
        if not tex._pdflatex(job, main.replace(os.sep, "/"), f"pass {number}", pdflatex):
            tex._show_error(job)
            return 1
        helpers = [tex._bibliography(job), tex._glossary(job), tex._index(job)]
        if not any(helpers) and not tex._needs_rerun(job):
            break
    pdf = os.path.join(out_folder, job + ".pdf")
    shutil.copyfile(os.path.join(tex.OUT, job + ".pdf"), pdf)
    print(f"written   {pdf}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m endgame_book.gamebook", description="Build a book of games.")
    parser.add_argument("book", help="the folder under games/, e.g. grandmaster-plays")
    parser.add_argument("--check", action="store_true", help="only check the moves, do not compile")
    args = parser.parse_args(argv)
    return build(args.book, not args.check)


if __name__ == "__main__":
    sys.exit(main())
