"""One program for the whole book: python -m endgame_book [options]

Each run:
  1. Statistics (Part I, the appendix, and endgames.tex, the list of endgame chapters in
     the order of study): written when missing, or when the data, the settings or the
     program changed since. A file you have edited is never replaced; you get a warning
     instead when it is out of date.
  2. Endgame chapters: each written only when its file is missing. After that it is yours.
The data is read only when something has to be written. scripts/make_book.bat then
compiles book.tex.
"""

import hashlib
import logging
import os
import re
from typing import List, Optional, Tuple

from . import latex, texts
from .build import APPENDIX, CHAPTERS, PART_ONE, position_entries
from .game_line import Shown, position_key
from .collect import collect
from .reader import find_files
from .sections import pawn_split, pieces_on_board, positions
from .stats import is_real_blunder, material
from .band import Band
from .stats import summarize

logger = logging.getLogger(__name__)
ROOK_CHAPTER = "rook-endgames.tex"
_STAMP = re.compile(r"^% Written by make_book from the data \((.*); check ([0-9a-f]{12})\)")


def _check(body: str) -> str:
    """Checksum of a file's text, the same whatever line endings an editor used."""
    lines = [line.rstrip() for line in body.replace("\r\n", "\n").split("\n")]
    return hashlib.sha1("\n".join(lines).strip().encode("utf-8")).hexdigest()[:12]


def program_version() -> str:
    """Checksum of the code that writes the statistics: a change to it refreshes them too."""
    here = os.path.dirname(os.path.abspath(__file__))
    digest = hashlib.sha1()
    for name in ("stats.py", "texts.py", "latex.py", "sections.py", "collect.py", "reader.py"):
        with open(os.path.join(here, name), "rb") as handle:
            digest.update(handle.read().replace(b"\r\n", b"\n"))
    return digest.hexdigest()[:8]


def stamped(body: str, settings: str) -> str:
    return (f"% Written by make_book from the data ({settings}; check {_check(body)})\n"
            "% If you edit this file, make_book keeps your version.\n" + body)


def file_state(path: str) -> Tuple[str, str]:
    """('missing' | 'edited' | 'generated', settings it was written with)."""
    if not os.path.exists(path):
        return "missing", ""
    with open(path, encoding="utf-8") as handle:
        first = handle.readline()
        handle.readline()                       # the second stamp line
        body = handle.read()
    if first.startswith("% Written by scripts/update_statistics.bat"):
        return "generated", ""                  # written by the earlier version, never edited
    match = _STAMP.match(first)
    if not match or match.group(2) != _check(body):
        return "edited", match.group(1) if match else ""
    return "generated", match.group(1)


ENDGAMES = "endgames.tex"
MIN_GAMES_FOR_CHAPTERS = 1000     # fewer games in a band: no endgame chapters are written yet
_LISTED = re.compile(r"^\\chapterfile\{([^}]*)\}.*% material: (.+?)\s*$", re.M)


def endgame_ok(key: str) -> bool:
    """Each side has at most two pieces besides king and pawns."""
    if key.startswith("B v B "):
        return True
    return all(side == "pawns" or len(side) <= 2 for side in key.split(" v "))


def chapter_name(key: str) -> str:
    """File name of an endgame's chapter: 'R v R' keeps its old name rook-endgames.tex."""
    if key == "R v R":
        return ROOK_CHAPTER
    return re.sub(r"[^a-z0-9]+", "-", texts.material_name(key).lower()).strip("-") + ".tex"


def chapter_label(key: str) -> str:
    return "ch:" + chapter_name(key)[:-4]


def simplicity(key: str) -> int:
    """0 for king and pawn endings, 1 for at most one piece a side, 2 for the rest."""
    sides = key.split(" v ")
    if all(side == "pawns" for side in sides):
        return 0
    return 1 if all(side == "pawns" or len(side.split()[0]) <= 1 for side in sides) else 2


def study_order(summary, count: int) -> List:
    """The first `count` endgames of chapter 3 (blunders per 100 games played) that fit endgame_ok,
    simplest first: king and pawn endings, then one piece a side, then two; within each, chapter 3's order.
    Walking before flying: the bigger endgames turn into the simpler ones."""
    rows = sorted(summary.by_material, key=lambda r: -r.blunders_per_100_all)
    chosen = [r for r in rows if endgame_ok(r.key)][:count]
    return sorted(chosen, key=lambda r: simplicity(r.key))


def render_endgames(rows, chapters_dir: str, games: Optional[int] = None) -> str:
    """The list of endgame chapters, in the order of study. book.tex includes it.
    With too few games in the band, a sentence for the reader instead of the list."""
    if games is not None and games < MIN_GAMES_FOR_CHAPTERS:
        return latex.esc(texts.no_chapters_yet(games, MIN_GAMES_FOR_CHAPTERS)) + "\n"
    lines = []
    for row in rows:
        path = f"{chapters_dir}/{chapter_name(row.key)}".replace(os.sep, "/")
        lines.append(f"\\chapterfile{{{path}}}{{run \\texttt{{scripts\\textbackslash make\\_book.bat}}}}"
                     f"  % material: {row.key}")
    return "\n".join(lines) + "\n"


def listed_chapters(path: str) -> List[Tuple[str, str]]:
    """(material, file) for each chapter listed in endgames.tex."""
    with open(path, encoding="utf-8") as handle:
        return [(m.group(2), m.group(1)) for m in _LISTED.finditer(handle.read())]


def render_chapter(row, rank: int, entries, exercises: Optional[dict] = None) -> str:
    return (f"\\chapter{{{texts.material_name(row.key)}}}\\label{{{chapter_label(row.key)}}}\n"
            + "\n\n".join(latex.esc(p) for p in texts.chapter_intro(row, rank)) + "\n\n"
            + latex.positions_latex(entries, exercises))


def choose_exercises(found, entries, shown: Shown, count: int) -> dict:
    """Pawn balance -> up to `count` FENs for each section of the chapter: positions with the same
    pawn balance, from games the chapter does not show, one per game, never a position shown before."""
    sections_ = {pawn_split(p.blunder["fen"]) for p, _items in entries}
    used_games = {p.game["game_id"] for p, _items in entries}
    used_keys = set(shown.positions)
    chosen: dict = {s: [] for s in sections_}
    for p in found:
        split = pawn_split(p.blunder["fen"])
        if split not in chosen or len(chosen[split]) >= count or p.game["game_id"] in used_games:
            continue
        key = position_key(p.blunder["fen"])
        if key in used_keys:
            continue
        used_games.add(p.game["game_id"])
        used_keys.add(key)
        chosen[split].append(p.blunder["fen"])
    return chosen


POSITIONS_JSON = "positions.json"


def positions_json(games, blunders, band: Band) -> str:
    """Every position of the band where a real blunder was made, with the answer: for other apps."""
    import json
    by_id = {g["game_id"]: g for g in games if band.ok(g)}
    items = []
    for b in blunders:
        g = by_id.get(b["game_id"])
        if g is None or not b["fen"] or not is_real_blunder(b):
            continue
        (more_pieces, more_pawns), (fewer_pieces, fewer_pawns) = pawn_split(b["fen"])
        number = lambda v: float(v) if v not in ("", None) else None
        items.append({
            "id": f"{b['game_id']}-{b['ply']}",
            "fen": b["fen"],
            "side_to_move": b["mover"],
            "material": material(b["signature"], b.get("kind", "")),
            "pawn_balance": texts.pawns_title(((more_pieces, more_pawns), (fewer_pieces, fewer_pawns))),
            "pieces_on_board": pieces_on_board(b["fen"]),
            "best_move": b["best"],
            "played_move": b["move"],
            "verdict_before": b["group_before"],
            "verdict_after": b["group_after"],
            "eval_before": number(b["eval_before"]),
            "eval_after": number(b["eval_after"]),
            "moves_that_hold": int(b["holding"]) if str(b["holding"]).isdigit() else None,
            "move_number": int(b["move_number"]),
            "lichess": latex.lichess_url(b["fen"]),
            "game": {"id": g["game_id"], "white": g["white"], "black": g["black"],
                     "white_elo": number(g["white_elo"]), "black_elo": number(g["black_elo"]),
                     "event": g["event"], "date": g["date"], "result": g["result"]},
        })
    return json.dumps({"band": band.describe(), "positions": items}, ensure_ascii=False, indent=1) + "\n"


def write_if_changed(path: str, text: str) -> bool:
    if os.path.exists(path) and open(path, encoding="utf-8").read() == text:
        return False
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return True


def band_file(band: Band) -> str:
    """books/<band>/band.tex: tells book.tex which band it is and where its chapters are."""
    return os.path.join(band.folder, "band.tex")


def write_band_file(band: Band) -> None:
    os.makedirs(band.folder, exist_ok=True)
    chapters = band.chapters.replace(os.sep, "/")
    text = ("% Written by make_book: the Elo band of this book.\n"
            f"\\providecommand{{\\egchapters}}{{{chapters}}}\n"
            f"\\providecommand{{\\egband}}{{{band.describe(latex=True)}}}\n")
    path = band_file(band)
    if not os.path.exists(path) or open(path, encoding="utf-8").read() != text:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)


def make(input_dir: str, band: Optional[Band] = None, chapters_dir: Optional[str] = None, min_games: int = 500,
         top: int = 15, show: Optional[int] = 30, per_section: Optional[int] = 10,
         keep_statistics: bool = False, endgames: int = 15, exercises: int = 10) -> List[str]:
    """Bring the chapter files up to date. Returns one line per file saying what happened.

    Statistics files (Part I, appendix, the list of endgame chapters) follow the rules above;
    with keep_statistics, existing ones are kept as they are. An endgame chapter is written
    only if its file does not exist, with `show` positions, at most `per_section` per pawn balance."""
    band = band or Band()
    chapters_dir = chapters_dir or band.chapters
    write_band_file(band)
    data_files = find_files(input_dir)
    if not data_files:
        raise FileNotFoundError(f"no *.annotated.pgn files under {input_dir}")
    data_time = max(os.path.getmtime(p) for p in data_files)
    settings = (f"band {band.slug}, min-games {min_games}, top {top}, endgames {endgames}, "
                f"program {program_version()}")
    os.makedirs(chapters_dir, exist_ok=True)

    report: List[str] = []
    stats_todo = []
    for name in (PART_ONE, ENDGAMES, APPENDIX):
        path = os.path.join(chapters_dir, name)
        state, written_with = file_state(path)
        stale = state != "missing" and (os.path.getmtime(path) < data_time or written_with != settings)
        if keep_statistics and state != "missing":
            report.append(f"kept      {path}  (--keep-statistics)")
        elif state == "missing" or (state == "generated" and stale):
            stats_todo.append(name)
        elif state == "edited" and stale:
            report.append(f"kept      {path}  WARNING: you edited it, and the data, the settings or the program have changed "
                          "since. To get new numbers, rename or delete it and run make_book again.")
        else:
            report.append(f"kept      {path}  ({'yours' if state == 'edited' else 'up to date'})")

    endgames_path = os.path.join(chapters_dir, ENDGAMES)
    listed = [] if ENDGAMES in stats_todo else listed_chapters(endgames_path)
    missing = [(key, path) for key, path in listed if not os.path.exists(path)]
    json_path = os.path.join(band.folder, POSITIONS_JSON)
    if not stats_todo and not missing and os.path.exists(json_path):
        report += [f"kept      {path}  (yours)" for _key, path in listed]
        return report

    logger.info("Reading the data ...")
    games, segments, blunders, _counts = collect(input_dir)
    summary = summarize(games, segments, blunders, band=band)
    order = study_order(summary, endgames)
    if write_if_changed(json_path, positions_json(games, blunders, band)):
        report.append(f"written   {json_path}  (all positions with a blunder, with the answers)")
    if stats_todo:
        has_chapters = summary.games >= MIN_GAMES_FOR_CHAPTERS
        book_order = [r.key for r in order] if has_chapters else None
        texts_ = {PART_ONE: latex.render_part_one(summary, min_games, top, has_chapters, book_order),
                  APPENDIX: latex.render_appendix(summary, min_games),
                  ENDGAMES: render_endgames(order, chapters_dir, summary.games)}
        for name in stats_todo:
            path = os.path.join(chapters_dir, name)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(stamped(texts_[name], settings))
            report.append(f"written   {path}")
        listed = listed_chapters(endgames_path)

    if summary.games < MIN_GAMES_FOR_CHAPTERS:
        report.append(f"not yet   endgame chapters: only {summary.games:,} games in this band "
                      f"(at least {MIN_GAMES_FOR_CHAPTERS:,} needed). Annotate more games for it first; "
                      "a chapter file is written once and then kept.")
        report += [f"kept      {path}  (yours)" for _key, path in listed if os.path.exists(path)]
        return report

    # Chapters already there (yours) come first, so new ones do not repeat their positions.
    shown = Shown()
    for _key, path in listed:
        if os.path.exists(path):
            shown.register_file(path)
            report.append(f"kept      {path}  (yours)")
    # rank = place among the endgames of this book (each side at most two pieces), as in endgames.tex
    rows = {r.key: (i, r) for i, r in enumerate(study_order(summary, len(summary.by_material)), 1)}
    kept_ids = {g["game_id"] for g in games if band.ok(g)}
    for key, path in listed:
        if os.path.exists(path) or key not in rows:
            continue
        rank, row = rows[key]
        found, _total = positions(games, blunders, kept_ids, wanted=key)
        entries = position_entries(input_dir, found, "notes", show, per_section, shown)
        practice = choose_exercises(found, entries, shown, exercises)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(render_chapter(row, rank, entries, practice))
        report.append(f"written   {path}  ({len(entries)} positions, "
                      f"{sum(len(v) for v in practice.values())} exercises)")
    return report
