"""Compile book.tex into output/book.pdf, doing only the work that is needed.

  1. Board cache: new \\diagram positions are drawn (boards.py); the rest are reused.
  2. Nothing changed since the last book.pdf: nothing is compiled.
  3. Otherwise pdflatex runs, printing each chapter as it gets there. The glossary is
     rebuilt only when it changed, and pdflatex runs again only when references moved.
     LaTeX's helper files (.aux, .toc, ...) stay in output/, so the next build needs
     fewer passes.

With only=CHAPTER (e.g. 'rook-endgames'), just that chapter is typeset into
output/draft.pdf; references to other chapters come from the last full build.
"""

import argparse
import filecmp
import os
import re
import shutil
import subprocess
import sys
import time
from typing import List, Optional

from . import boards

OUT = "output"
BOOK = "book"
MAX_PASSES = 4
_CHAPTER = re.compile(r"\((?:\./)?((?:chapters|cards)/[^\s()]+\.tex)")
_RERUN = re.compile(r"Rerun to get|Label\(s\) may have changed|There were undefined references|"
                    r"Please rerun LaTeX|undefined references")


def _inputs() -> List[str]:
    files = ["book.tex", "endgame.sty", "board-style.tex", os.path.join(boards.CACHE, "boards.tex")]
    return [f for f in files + boards.tex_files() if os.path.exists(f)]


def up_to_date(pdf: str) -> bool:
    if not os.path.exists(pdf):
        return False
    built = os.path.getmtime(pdf)
    return all(os.path.getmtime(f) <= built for f in _inputs())


def _pdflatex(job: str, source: str, label: str, pdflatex: str) -> bool:
    """One pass, printing chapters as pdflatex reaches them. Returns True on success."""
    started = time.time()
    print(f"{label} ...", flush=True)
    cmd = [pdflatex, "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={OUT}",
           f"-jobname={job}", source]
    seen, recent = set(), ""
    env = dict(os.environ, max_print_line="10000")     # TeX Live: do not wrap the output lines
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace",
                            env=env)
    for line in proc.stdout:
        text = recent + line.rstrip("\r\n")              # joined, so a wrapped file name is still found
        recent = text[-300:]
        for name in _CHAPTER.findall(text):
            if name not in seen:
                seen.add(name)
                print(f"    {name}", flush=True)
    proc.wait()
    print(f"  {time.time() - started:.0f} s", flush=True)
    return proc.returncode == 0


def _show_error(job: str) -> None:
    log = os.path.join(OUT, job + ".log")
    print(f"pdflatex failed. The error (full log: {log}):")
    if os.path.exists(log):
        with open(log, encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
        for i, line in enumerate(lines):
            if line.startswith("!"):
                print("\n".join("  " + l for l in lines[i:i + 4]))
                break


def _needs_rerun(job: str) -> bool:
    log = os.path.join(OUT, job + ".log")
    with open(log, encoding="utf-8", errors="replace") as handle:
        return bool(_RERUN.search(handle.read()))


def _glossary(job: str) -> bool:
    """Run makeglossaries if the glossary entries changed. Returns True if it ran."""
    glo = os.path.join(OUT, job + ".glo")
    last = glo + ".last"
    if not os.path.exists(glo) or (os.path.exists(last) and filecmp.cmp(glo, last, shallow=False)):
        return False
    tool = shutil.which("makeglossaries")
    if not tool:
        print("makeglossaries not found: the glossary is left out.")
        return False
    print("Glossary ...", flush=True)
    result = subprocess.run([tool, job], cwd=OUT, capture_output=True, text=True, errors="replace")
    if result.returncode != 0:
        print(f"makeglossaries failed: the glossary is left out. See {os.path.join(OUT, job + '.glg')}")
        return False
    shutil.copyfile(glo, last)
    return True


def compile_book(only: Optional[str] = None, force: bool = False) -> int:
    pdflatex = shutil.which("pdflatex")
    if not pdflatex:
        print("pdflatex was not found. Install MiKTeX: https://miktex.org/download")
        return 1
    os.makedirs(OUT, exist_ok=True)
    new, total = boards.update(pdflatex=pdflatex)
    print(f"Boards: {total} in the book, {new} drawn now, {total - new} from the cache.")

    if only:
        chapter = only if only.endswith(".tex") else only + ".tex"
        chapter = chapter if "/" in chapter.replace("\\", "/") else f"chapters/{chapter}"
        chapter = chapter.replace("\\", "/")
        if not os.path.exists(chapter):
            print(f"{chapter} not found.")
            return 1
        for ext in (".aux", ".toc", ".gls"):                # references from the last full build
            if os.path.exists(os.path.join(OUT, BOOK + ext)):
                shutil.copyfile(os.path.join(OUT, BOOK + ext), os.path.join(OUT, "draft" + ext))
        source = (f"\\def\\egonly{{{chapter}}}\\def\\eglist{{chapters/endgames.tex}}\\input{{book.tex}}")
        if not _pdflatex("draft", source, f"Draft of {chapter}", pdflatex):
            _show_error("draft")
            return 1
        print(f"Written: {os.path.join(OUT, 'draft.pdf')}")
        return 0

    pdf = os.path.join(OUT, BOOK + ".pdf")
    if not force and up_to_date(pdf):
        print(f"Nothing changed since the last build: {pdf} is up to date.")
        return 0
    started = time.time()
    for number in range(1, MAX_PASSES + 1):
        if not _pdflatex(BOOK, "book.tex", f"pdflatex, pass {number}", pdflatex):
            _show_error(BOOK)
            return 1
        glossary = _glossary(BOOK)
        if not glossary and not _needs_rerun(BOOK):
            break
    print(f"Written: {pdf} ({time.time() - started:.0f} s)")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m endgame_book.compile", description="Compile the book.")
    parser.add_argument("--only", metavar="CHAPTER", help="typeset only this chapter into output/draft.pdf, "
                                                          "e.g. rook-endgames")
    parser.add_argument("--force", action="store_true", help="compile even if nothing changed")
    args = parser.parse_args(argv)
    return compile_book(args.only, args.force)


if __name__ == "__main__":
    sys.exit(main())
