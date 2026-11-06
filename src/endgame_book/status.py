"""What the author wants to see after a build: for each chapter, are all its diagrams commented?

Read from the written chapter files, so it works whether or not make_book rewrote them. A diagram
counts as commented when a comment of yours is printed in its line: a note on the diagram's move,
on a later move, or a 'start'/'end' note. A note that belongs to another diagram does not count: when
a game runs into a position that is a diagram of its own (often in the other book), that diagram's note
is printed there too, but it does not comment on this one."""

import os
import re
from typing import List, Tuple

_LISTED = re.compile(r"^(?:\\egbook\{(\w+)\}\{)?\\chapterfile\{([^}]*)\}", re.M)
_CHAPTER = re.compile(r"\\chapter\{([^}]*)\}")
_DIAGRAM = re.compile(r"^\\diagram\[([^\]]+)\]")
_END = re.compile(r"^(% note: @|\\section|\\begin\{exercises\})")
_NOT_A_COMMENT = re.compile(r"^(\\moves\{|\\game\{|\\diagram|\\seen\{|\\libunit\{|\\yourtext\{|%|"
                            r"(1-0|0-1|1/2-1/2|\*)\\par$|$)")


_KEY = re.compile(r"^% note: @ (\S+ [wb])[^|]*\| (\S+?)[?!]*$")


def _line(text: str) -> str:
    return text.strip()[:-len("\\par")].strip() if text.strip().endswith("\\par") else text.strip()


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


def chapter_status(path: str, others: dict = None) -> Tuple[str, int, List[str]]:
    """(chapter title, diagrams, labels of the diagrams without a comment). others: diagram_note_lines."""
    others = others or {}
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().split("\n")
    title = next((m.group(1) for m in map(_CHAPTER.search, lines) if m), os.path.basename(path))
    total, missing, label, commented, own = 0, [], None, False, None

    def close():
        if label is not None and not commented:
            missing.append(label)

    previous = ""
    for line in lines:
        start_of_game = previous.startswith("\\game{")
        previous = line
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
        elif label is not None and not _NOT_A_COMMENT.match(line.strip()):
            foreign = any(_line(line) in text for k, text in others.items() if k != own)
            commented = commented or not foreign
    close()
    return title, total, missing


def books_status(chapters_dir: str) -> List[Tuple[str, List[Tuple[str, int, List[str]]]]]:
    """[(book 'one'|'two', [chapter status, ...]), ...] in the order of endgames.tex."""
    listing = os.path.join(chapters_dir, "endgames.tex")
    if not os.path.exists(listing):
        return []
    books: dict = {}
    others = diagram_note_lines(chapters_dir)
    with open(listing, encoding="utf-8") as handle:
        for book, path in _LISTED.findall(handle.read()):
            if os.path.exists(path):
                books.setdefault(book or "one", []).append(chapter_status(path, others))
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
        width = max(len(title) for title, _t, _m in chapters)
        for title, total, missing in chapters:
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
    return "\n".join(out)
