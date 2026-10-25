"""Board cache: every \\diagram position is drawn once and kept as a page of a PDF in output/boards.

Before the book is compiled, the program collects the positions of all \\diagram commands in
the chapter and card files. Positions not drawn yet are drawn together in one pdflatex run
(a new batch-N.pdf); the others are taken from the cache. output/boards/boards.tex tells
endgame.sty where each board is; a position not in it is drawn in the book as before.
Delete output/boards to redraw everything (e.g. after changing board-style.tex).
"""

import json
import os
import re
import subprocess
import time
from typing import Dict, List, Tuple

CACHE = os.path.join("output", "boards")
_DIAGRAM = re.compile(r"\\(?:diagram|exercise)(?:\[[^\]]*\])?\{([^}]*)\}")
_PAGES = re.compile(r"Output written on .*?\((\d+) pages?")


def tex_files(roots=("chapters", "cards")) -> List[str]:
    found = []
    for root in roots:
        for folder, _dirs, names in os.walk(root):
            found += [os.path.join(folder, n) for n in names if n.endswith(".tex")]
    return sorted(found)


def positions_in(files: List[str]) -> List[str]:
    """FENs of all \\diagram and \\exercise commands, in order, without repeats."""
    fens: Dict[str, None] = {}
    for path in files:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for fen in _DIAGRAM.findall(handle.read()):
                fens.setdefault(fen.strip(), None)
    return list(fens)


def _style_path() -> str:
    return os.path.abspath("board-style.tex").replace(os.sep, "/")


def _batch_tex(fens: List[str]) -> str:
    pages = "\n".join(f"\\begin{{egpage}}\\egboard{{{fen}}}\\end{{egpage}}" for fen in fens)
    return ("\\documentclass[border=3pt]{standalone}\n\\usepackage{chessboard}\n"
            f"\\input{{{_style_path()}}}\n"
            "\\newenvironment{egpage}{}{}\n\\standaloneenv{egpage}\n"
            f"\\begin{{document}}\n{pages}\n\\end{{document}}\n")


def _map_tex(index: Dict[str, Tuple[str, int]], cache: str) -> str:
    folder = cache.replace(os.sep, "/")
    lines = ["% Written by the board cache: where each board is. Do not edit."]
    for fen, (pdf, page) in index.items():
        lines.append(f"\\expandafter\\def\\csname eg@board@{fen}\\endcsname{{{{{folder}/{pdf}}}{{{page}}}}}")
    return "\n".join(lines) + "\n"


def update(cache: str = CACHE, files: List[str] = None, pdflatex: str = "pdflatex") -> Tuple[int, int]:
    """Draw the boards that are not cached yet. Returns (new boards, all boards)."""
    files = tex_files() if files is None else files
    fens = positions_in(files)
    os.makedirs(cache, exist_ok=True)
    index_path = os.path.join(cache, "index.json")
    index: Dict[str, Tuple[str, int]] = {}
    if os.path.exists(index_path):
        with open(index_path, encoding="utf-8") as handle:
            index = {k: tuple(v) for k, v in json.load(handle).items()}
        index = {k: v for k, v in index.items() if os.path.exists(os.path.join(cache, v[0]))}
    new = [fen for fen in fens if fen not in index]
    if new:
        number = 1 + max([int(re.search(r"\d+", v[0]).group()) for v in index.values()] or [0])
        name = f"batch-{number}"
        with open(os.path.join(cache, name + ".tex"), "w", encoding="utf-8") as handle:
            handle.write(_batch_tex(new))
        print(f"Drawing {len(new)} new board{'s' if len(new) != 1 else ''} ...", flush=True)
        started = time.time()
        result = subprocess.run([pdflatex, "-interaction=nonstopmode", "-halt-on-error", name + ".tex"],
                                cwd=cache, capture_output=True, text=True, errors="replace")
        pages = _PAGES.search(result.stdout)
        if result.returncode != 0 or not pages or int(pages.group(1)) != len(new):
            # Not fatal: boards that are not cached are drawn in the book itself.
            print(f"  could not draw the boards (see {os.path.join(cache, name + '.log')}); "
                  "the book draws them itself this time.")
        else:
            for page, fen in enumerate(new, 1):
                index[fen] = (name + ".pdf", page)
            print(f"  done in {time.time() - started:.0f} s", flush=True)
            for ext in (".aux", ".log", ".tex"):
                path = os.path.join(cache, name + ext)
                if os.path.exists(path):
                    os.remove(path)
    _write_if_changed(index_path, json.dumps(index, indent=0))
    _write_if_changed(os.path.join(cache, "boards.tex"),
                      _map_tex({k: v for k, v in index.items() if k in set(fens)}, cache))
    return len(new), len(fens)


def _write_if_changed(path: str, text: str) -> None:
    """Leave an unchanged file alone, so its date shows the book needs no new build."""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            if handle.read() == text:
                return
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
