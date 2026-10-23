"""One run: annotated PGN files -> report.html, report.tex, report.pdf. Nothing else is kept."""

import logging
import os
import shutil
import subprocess
from typing import Dict, Optional

from . import html, latex
from .collect import collect
from .stats import summarize

logger = logging.getLogger(__name__)
LATEX_LEFTOVERS = (".aux", ".log", ".out")


def compile_pdf(tex_path: str) -> Optional[str]:
    """Run pdflatex next to the .tex file; remove its helper files. Returns the PDF path or None."""
    pdflatex = shutil.which("pdflatex")
    if not pdflatex:
        logger.warning("pdflatex not found: wrote HTML and LaTeX, no PDF. Install MiKTeX or TeX Live.")
        return None
    folder, name = os.path.split(os.path.abspath(tex_path))
    stem = os.path.splitext(name)[0]
    result = subprocess.run([pdflatex, "-interaction=nonstopmode", "-halt-on-error", name],
                            cwd=folder, capture_output=True, text=True, errors="replace")
    if result.returncode != 0:
        tail = "\n".join(result.stdout.splitlines()[-15:])
        raise RuntimeError(f"pdflatex failed; see {os.path.join(folder, stem + '.log')}\n{tail}")
    for ext in LATEX_LEFTOVERS:
        leftover = os.path.join(folder, stem + ext)
        if os.path.exists(leftover):
            os.remove(leftover)
    return os.path.join(folder, stem + ".pdf")


def build(input_dir: str, out_dir: str, name: str = "report", min_elo: Optional[int] = None,
          min_games: int = 100, top: int = 25, pdf: bool = True) -> Dict[str, str]:
    games, segments, blunders, _counts = collect(input_dir)
    summary = summarize(games, segments, blunders, min_elo)
    os.makedirs(out_dir, exist_ok=True)
    written = {}
    html_path = os.path.join(out_dir, name + ".html")
    with open(html_path, "w", encoding="utf-8") as handle:
        handle.write(html.render(summary, min_games, top))
    written["html"] = html_path
    tex_path = os.path.join(out_dir, name + ".tex")
    with open(tex_path, "w", encoding="utf-8") as handle:
        handle.write(latex.render(summary, min_games, top))
    written["tex"] = tex_path
    if pdf:
        pdf_path = compile_pdf(tex_path)
        if pdf_path:
            written["pdf"] = pdf_path
    logger.info("%d games in the report. Written: %s", summary.games, ", ".join(written.values()))
    return written
