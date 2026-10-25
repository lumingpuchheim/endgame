"""Compile book.tex into output/book.pdf, doing only the work that is needed.

  1. Board cache: new \\diagram positions are drawn (boards.py); the rest are reused.
  2. Nothing changed since the last book.pdf: nothing is compiled.
  3. Otherwise pdflatex runs, printing each chapter as it gets there. The glossary and the
     index are rebuilt only when they changed, and pdflatex runs again only when references moved.
     LaTeX's helper files (.aux, .toc, ...) stay in output/, so the next build needs
     fewer passes.

Each Elo band has its own folder books/<band> (band.py): chapters, the PDF
Endgames-Elo-<band>.pdf, and LaTeX's helper files in build/.

With only=CHAPTER (e.g. 'rook-endgames'), just that chapter is typeset into
books/<band>/draft.pdf; references to other chapters come from the last full build.
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
from .band import RULES, Band

OUT = "output"                 # set per band by compile_book: books/<band>/build
MAX_PASSES = 4
_CHAPTER = re.compile(r"\((?:\./)?((?:books/[^\s()/]+/)?(?:chapters|cards|texts)/[^\s()]+\.tex)")
_RERUN = re.compile(r"Rerun to get|Label\(s\) may have changed|There were undefined references|"
                    r"Please rerun LaTeX|undefined references")


def _inputs(band: Band) -> List[str]:
    files = ["book.tex", "endgame.sty", "board-style.tex", "endgame.ist", "introduction.tex", "refs.bib",
             os.path.join(boards.CACHE, "boards.tex"),
             os.path.join(band.folder, "band.tex")]
    return [f for f in files + boards.tex_files(source_folders(band)) if os.path.exists(f)]


def source_folders(band: Band) -> tuple:
    """Folders whose .tex files go into the book: the chapters, your texts and notes, the idea files."""
    return (band.chapters, os.path.join(band.folder, "texts"), "texts", "notes", "cards")


def up_to_date(pdf: str, band: Band) -> bool:
    if not os.path.exists(pdf):
        return False
    built = os.path.getmtime(pdf)
    return all(os.path.getmtime(f) <= built for f in _inputs(band))


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


def _helper(job: str, ext: str, name: str, command: List[str], log_ext: str) -> bool:
    """Run makeglossaries / makeindex if their input (job+ext) changed. Returns True if it ran."""
    src = os.path.join(OUT, job + ext)
    last = src + ".last"
    if not os.path.exists(src) or (os.path.exists(last) and filecmp.cmp(src, last, shallow=False)):
        return False
    tool = shutil.which(command[0])
    if not tool:
        print(f"{command[0]} not found: the {name} is left out.")
        return False
    print(f"{name.capitalize()} ...", flush=True)
    result = subprocess.run([tool] + command[1:], cwd=OUT, capture_output=True, text=True, errors="replace")
    if result.returncode != 0:
        print(f"{command[0]} failed: the {name} is left out. See {os.path.join(OUT, job + log_ext)}")
        return False
    shutil.copyfile(src, last)
    return True


def _glossary(job: str) -> bool:
    return _helper(job, ".glo", "glossary", ["makeglossaries", job], ".glg")


def _bibliography(job: str) -> bool:
    folder = os.path.abspath(".")                    # refs.bib is in the repository folder
    return _helper(job, ".bcf", "bibliography", ["biber", "--input-directory", folder, job], ".blg")


def _index(job: str) -> bool:
    style = os.path.abspath("endgame.ist")
    return _helper(job, ".idx", "index", ["makeindex", "-s", style, job + ".idx"], ".ilg")


def compile_book(only: Optional[str] = None, force: bool = False, band: Optional[Band] = None) -> int:
    """Compile the book of one Elo band into books/<band>/Endgames-Elo-<band>.pdf."""
    global OUT
    band = band or Band()
    band_tex = os.path.join(band.folder, "band.tex")
    if not os.path.exists(band_tex):
        print(f"{band_tex} not found: run make_book.bat with the same Elo options first.")
        return 1
    pdflatex = shutil.which("pdflatex")
    if not pdflatex:
        print("pdflatex was not found. Install MiKTeX: https://miktex.org/download")
        return 1
    OUT = os.path.join(band.folder, "build")
    os.makedirs(OUT, exist_ok=True)
    new, total = boards.update(files=boards.tex_files(source_folders(band)), pdflatex=pdflatex)
    print(f"Boards: {total} in the book, {new} drawn now, {total - new} from the cache.")
    head = f"\\input{{{band_tex.replace(os.sep, '/')}}}"
    chapters = band.chapters.replace(os.sep, "/")

    if only:
        name = os.path.basename(only.replace("\\", "/"))
        chapter = f"{chapters}/{name if name.endswith('.tex') else name + '.tex'}"
        if not os.path.exists(chapter):
            print(f"{chapter} not found.")
            return 1
        for ext in (".aux", ".toc", ".gls", ".ind", ".bbl"):  # references from the last full build
            if os.path.exists(os.path.join(OUT, band.job + ext)):
                shutil.copyfile(os.path.join(OUT, band.job + ext), os.path.join(OUT, "draft" + ext))
        source = f"\\def\\egonly{{{chapter}}}\\def\\eglist{{{chapters}/endgames.tex}}{head}\\input{{book.tex}}"
        if not _pdflatex("draft", source, f"Draft of {chapter}", pdflatex):
            _show_error("draft")
            return 1
        target = os.path.join(band.folder, "draft.pdf")
        shutil.copyfile(os.path.join(OUT, "draft.pdf"), target)
        print(f"Written: {target}")
        return 0

    pdf = os.path.join(band.folder, band.job + ".pdf")
    if not force and up_to_date(pdf, band):
        print(f"Nothing changed since the last build: {pdf} is up to date.")
        return 0
    started = time.time()
    for number in range(1, MAX_PASSES + 1):
        if not _pdflatex(band.job, f"{head}\\input{{book.tex}}", f"pdflatex, pass {number}", pdflatex):
            _show_error(band.job)
            return 1
        helpers = [_bibliography(band.job), _glossary(band.job), _index(band.job)]  # all always checked
        if not any(helpers) and not _needs_rerun(band.job):
            break
    shutil.copyfile(os.path.join(OUT, band.job + ".pdf"), pdf)
    print(f"Written: {pdf} ({time.time() - started:.0f} s)")
    return 0


def add_band_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--min-elo", type=int, help="lowest rating (see --elo-rule)")
    parser.add_argument("--max-elo", type=int, help="highest rating (see --elo-rule)")
    parser.add_argument("--elo-rule", choices=RULES, default="both",
                        help="the limits apply to both players (default) or to their average")


def band_from(args) -> Band:
    return Band(args.min_elo, args.max_elo, args.elo_rule)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m endgame_book.compile", description="Compile the book.")
    add_band_options(parser)
    parser.add_argument("--only", metavar="CHAPTER", help="typeset only this chapter into books/<band>/draft.pdf, "
                                                          "e.g. rook-endgames")
    parser.add_argument("--force", action="store_true", help="compile even if nothing changed")
    args, _other = parser.parse_known_args(argv)        # list_positions.bat passes its own options too
    return compile_book(args.only, args.force, band_from(args))


if __name__ == "__main__":
    sys.exit(main())
