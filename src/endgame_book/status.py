"""What the author wants to see after a build: for each chapter, are all its diagrams commented?

Read from the written chapter files, so it works whether or not make_book rewrote them. A diagram
counts as commented when any comment of yours is printed in its line: a note on the diagram's move,
on a later move, or a 'start'/'end' note."""

import os
import re
from typing import List, Tuple

_LISTED = re.compile(r"^(?:\\egbook\{(\w+)\}\{)?\\chapterfile\{([^}]*)\}", re.M)
_CHAPTER = re.compile(r"\\chapter\{([^}]*)\}")
_DIAGRAM = re.compile(r"^\\diagram\[([^\]]+)\]")
_END = re.compile(r"^(% note: @|\\section|\\begin\{exercises\})")
_NOT_A_COMMENT = re.compile(r"^(\\moves\{|\\game\{|\\diagram|\\seen\{|\\libunit\{|\\yourtext\{|%|"
                            r"(1-0|0-1|1/2-1/2|\*)\\par$|$)")


def chapter_status(path: str) -> Tuple[str, int, List[str]]:
    """(chapter title, diagrams, labels of the diagrams without a comment)."""
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().split("\n")
    title = next((m.group(1) for m in map(_CHAPTER.search, lines) if m), os.path.basename(path))
    total, missing, label, commented = 0, [], None, False

    def close():
        if label is not None and not commented:
            missing.append(label)

    for line in lines:
        start = _DIAGRAM.match(line)
        if start or _END.match(line):
            close()
            label, commented = (start.group(1), False) if start else (None, False)
            total += bool(start)
        elif label is not None and not _NOT_A_COMMENT.match(line.strip()):
            commented = True
    close()
    return title, total, missing


def books_status(chapters_dir: str) -> List[Tuple[str, List[Tuple[str, int, List[str]]]]]:
    """[(book 'one'|'two', [chapter status, ...]), ...] in the order of endgames.tex."""
    listing = os.path.join(chapters_dir, "endgames.tex")
    if not os.path.exists(listing):
        return []
    books: dict = {}
    with open(listing, encoding="utf-8") as handle:
        for book, path in _LISTED.findall(handle.read()):
            if os.path.exists(path):
                books.setdefault(book or "one", []).append(chapter_status(path))
    return list(books.items())


BOOK_NAMES = {"one": "Book 1: king and pawns, one piece a side", "two": "Book 2: two pieces a side"}


def report(chapters_dir: str, numbers=None) -> str:
    """One line per chapter; diagrams to do by their number in the last compiled book (else their label)."""
    numbers = numbers or {}
    name = lambda label: f"{numbers[label]}" if label in numbers else label
    out = []
    for book, chapters in books_status(chapters_dir):
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
