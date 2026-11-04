"""The library: basic knowledge (a rule, a typical position) that a book prints only if it uses it.

A unit is a file lib/<name>.tex. A note or a text uses it by referring to it, with
\\xref{Section}{<name>} or \\uses{<name>}. When make_book writes the chapters, in book order, it puts
each unit that is used into the book once, just before the first position (or own text) that uses
it, together with the units that unit uses itself. Units that no position uses are left out, so
every band's book is complete on its own.
"""

import os
import re
from typing import Dict, List, Set

FOLDER = "lib"


def units(folder: str = FOLDER) -> Dict[str, str]:
    """{name: text} for every lib/<name>.tex."""
    found = {}
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            if name.endswith(".tex"):
                with open(os.path.join(folder, name), encoding="utf-8") as handle:
                    found[name[:-len(".tex")]] = handle.read()
    return found


def calls(text: str, names) -> List[str]:
    """The units a text uses, in the order of their first use."""
    used: List[str] = []
    text = re.sub(r"(?<!\\)%.*", "", text)                  # LaTeX comments do not count
    for match in re.finditer(r"\\(?:xref\{[^}]*\}|uses)\{([^}]+)\}", text):
        name = match.group(1)
        if name in names and name not in used:
            used.append(name)
    return used


def _with_dependencies(name: str, library: Dict[str, str], included: Set[str], out: List[str]) -> None:
    if name in included:
        return
    included.add(name)
    for dep in calls(library[name], library):
        _with_dependencies(dep, library, included, out)
    out.append(name)


def _own_text(line: str, text_folders) -> str:
    match = re.match(r"\\yourtext\{([^}]+)\}", line.strip())
    if not match:
        return ""
    for folder in reversed(text_folders):                 # the band's own texts win, as in endgame.sty
        path = os.path.join(folder, match.group(1) + ".tex")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as handle:
                return handle.read()
    return ""


def link(chapter: str, library: Dict[str, str], included: Set[str], text_folders=()) -> str:
    """The chapter with \\libunit{<name>} before the first position or own text that uses a unit
    not yet in the book. `included` collects the units already placed, across the chapters."""
    if not library:
        return chapter
    lines = chapter.split("\n")
    out: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("% note: @ "):                  # a position: up to the next one or section
            j = i + 1
            while j < len(lines) and not lines[j].startswith(("% note: @ ", "\\section", "\\yourtext")):
                j += 1
            block, body = lines[i:j], "\n".join(lines[i:j])
            i = j
        else:
            block, body = [line], _own_text(line, text_folders)
            i += 1
        new: List[str] = []
        for name in calls(body, library):
            _with_dependencies(name, library, included, new)
        out += [f"\\libunit{{{name}}}" for name in new] + block
    return "\n".join(out)
