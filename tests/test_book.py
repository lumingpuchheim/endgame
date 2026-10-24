import os
import re
import shutil

import pytest

from endgame_book.build import write_statistics
from endgame_book.collect import collect
from endgame_book.reader import find_files, iter_games
from endgame_book.stats import is_real_blunder, lasting_segments, material, summarize

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_files_found_in_issue_order_and_subfolders():
    names = [os.path.basename(p) for p in find_files(FIXTURES)]
    assert names == ["repeat.annotated.pgn", "sample.annotated.pgn"]   # the subfolder is searched too


def test_segments_and_blunders_read_from_comments():
    games = {g.game_id: g for g in iter_games(os.path.join(FIXTURES, "sample.annotated.pgn"))}
    assert not games["000000000001"].endgame and games["000000000001"].segments == []
    g = games["000000000002"]
    assert [(s.signature, s.moves) for s in g.segments] == [("RN-RB", 2), ("R-RB", 3)]
    first, second = g.blunders
    # 3. Rd2?? happened in the R-RB segment; the FEN is the one written before it
    assert (first.move_number, first.mover, first.move, first.signature) == (3, "white", "Rd2", "R-RB")
    assert first.fen == "4k3/8/8/8/8/8/8/3R1Kb1 w - - 0 3"
    assert (first.eval_before, first.eval_after) == (-0.20, -1.80)
    assert (second.move, second.best) == ("Kg2", "Kg2")


def test_only_real_blunders_count():
    games, segments, blunders, _ = collect(FIXTURES)
    assert [is_real_blunder(b) for b in blunders] == [True, False]   # 4. Kg2 was the engine's best move


def test_duplicate_game_counted_once():
    games, _, _, counts = collect(FIXTURES)
    assert counts["duplicates"] == 1 and len(games) == 3


def test_material_is_colour_neutral():
    assert material("RN-RB") == material("RB-RN") == "RB v RN"
    assert material("R-") == "R v pawns" and material("-") == "pawns v pawns"


def test_summary_numbers_and_min_elo():
    games, segments, blunders, _ = collect(FIXTURES)
    all_games = summarize(games, segments, blunders)
    assert (all_games.games, all_games.games_with_endgame) == (3, 2)
    strong = summarize(games, segments, blunders, min_elo=2600)
    assert strong.games == 2                                         # the 2400 player's game is out
    by = {r.key: r for r in strong.by_material}
    assert by["R v RB"].games == 1 and by["R v RB"].blunders == 1
    assert by["R v RB"].per_100_games == 50.0
    assert by["R v RB"].blunders_per_100_all == 50.0     # 1 blunder in 2 games played
    assert "R v R" not in by


def test_mixed_settings_refused(tmp_path):
    shutil.copy(os.path.join(FIXTURES, "sample.annotated.pgn"), tmp_path / "a.annotated.pgn")
    text = open(os.path.join(FIXTURES, "sample.annotated.pgn"), encoding="utf-8").read()
    (tmp_path / "b.annotated.pgn").write_text(
        text.replace('AnnotationDepth "15"', 'AnnotationDepth "20"').replace("00000000000", "10000000000"),
        encoding="utf-8")
    with pytest.raises(ValueError, match="mixes settings"):
        collect(str(tmp_path))


def test_unknown_format_refused(tmp_path):
    text = open(os.path.join(FIXTURES, "sample.annotated.pgn"), encoding="utf-8").read()
    (tmp_path / "x.annotated.pgn").write_text(text.replace("twic 0.2.0", "twic 9.9.9"), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown format"):
        collect(str(tmp_path))


def test_statistics_write_part_one_and_appendix_only(tmp_path):
    chapters = tmp_path / "chapters"
    write_statistics(FIXTURES, str(chapters), min_games=1)
    assert sorted(os.listdir(chapters)) == ["how-the-numbers-were-made.tex", "where-the-mistakes-are.tex"]
    part = (chapters / "where-the-mistakes-are.tex").read_text(encoding="utf-8")
    assert "\\documentclass" not in part and "includegraphics" not in part and "report" not in part.lower()
    assert part.count("\\chapter{") == 3 and "Rook vs rook and bishop" in part
    assert "\\chapter{How the Numbers Were Made}" in (chapters / "how-the-numbers-were-made.tex").read_text(encoding="utf-8")


def test_material_names_for_readers():
    from endgame_book.texts import material_name, pawns_title
    assert material_name("R v R") == "Rook vs rook"
    assert material_name("RB v RN") == "Rook and bishop vs rook and knight"
    assert material_name("RR v RR") == "Two rooks vs two rooks"
    assert material_name("pawns v pawns") == "King and pawns"
    assert material_name("R v pawns") == "Rook vs pawns"
    assert material_name("B v B opposite") == "Bishop vs bishop, opposite colours"
    from endgame_book.stats import material
    assert material("B-B", "bishop_same") == "B v B same" and material("B-B", "bishop_opposite") == "B v B opposite"
    assert material("B-B") == "B v B" and material("RB-R", "mixed") == "R v RB"
    from endgame_book.sections import pawn_split
    assert pawns_title(pawn_split("8/8/8/8/8/2k5/r4PP1/4K2R w - - 0 1")) == "Rook and two pawns vs rook"
    assert pawns_title(pawn_split("8/8/p7/8/8/2k5/r4P2/4K2R w - - 0 1")) == "Rook and pawn vs rook and pawn"
    assert pawns_title(pawn_split("6R1/8/p7/2r5/1k6/5K2/8/8 b - - 2 59")) == "Rook and pawn vs rook"


def test_book_files_fit_together():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    book = open(os.path.join(root, "book.tex"), encoding="utf-8").read()
    assert "\\usepackage{endgame}" in book and "report" not in book.lower()
    assert "\\chapterfile{introduction.tex}" in book and "grandmaster" not in book.lower()
    for chapter in ("where-the-mistakes-are", "endgames", "how-the-numbers-were-made"):
        assert f"\\egchapters/{chapter}.tex" in book
    sty = open(os.path.join(root, "endgame.sty"), encoding="utf-8").read()
    for macro in ("\\game", "\\diagram", "\\moves", "\\seen", "\\K", "\\bookcover", "\\chapterfile"):
        assert "\\newcommand{" + macro in sty


def test_exchange_in_progress_counts_as_the_material_before():
    segs = [{"order": "0", "moves": "6"},     # RB v RB stands for 6 moves
            {"order": "1", "moves": "1"},     # bishop taken ...
            {"order": "2", "moves": "9"}]     # ... and retaken: R v R
    assert lasting_segments(segs) == {0: 0, 1: 0, 2: 2}
    assert lasting_segments([{"order": "0", "moves": "1"}, {"order": "1", "moves": "4"}]) == {0: 1, 1: 1}


def test_positions_simplest_first():
    from endgame_book.sections import pieces_on_board, positions
    games, _, blunders, _ = collect(FIXTURES)
    shown, found = positions(games, blunders, {g["game_id"] for g in games}, wanted="R v RB")
    assert found == 1                                                  # 4. Kg2 was the engine's move: not shown
    assert shown[0].blunder["move"] == "Rd2"
    assert shown[0].pieces == pieces_on_board("4k3/8/8/8/8/8/8/3R1Kb1 w - - 0 3") == 4


def test_line_marks_blunder_and_stops_at_shown_position():
    from endgame_book.game_line import Shown, build_line
    from endgame_book.reader import Move
    fen = "6R1/8/p7/2r5/1k6/5K2/8/8 b - - 2 59"
    moves = [Move(1, 59, False, "a5", -0.15, {"before": "winning", "after": "equal", "best": "Re5", "holding": "1"}),
             Move(2, 60, True, "Ke2", -0.03, {}), Move(3, 60, False, "Kb3", -0.06, {}),
             Move(4, 61, True, "Kd2", -0.01, {})]
    shown = Shown()
    items = build_line(fen, moves, 1, "0-1", {}, shown)
    assert [k for k, _ in items] == ["diagram", "moves", "end"]
    assert [(m.san, mark) for m, mark in items[1][1]] == [("a5", "?"), ("Ke2", ""), ("Kb3", ""), ("Kd2", "")]
    assert items[2][1] == "0-1"                                        # no guess about why
    # a second game reaching the same position is not shown again
    assert build_line(fen, moves, 1, "0-1", {}, shown) == [("seen", "diagram-1")]


def test_example_section_in_latex(tmp_path):
    from endgame_book.latex import lichess_url
    assert lichess_url("8/8/p7/2r5 b - - 2 59") == "https://lichess.org/analysis/standard/8/8/p7/2r5_b_-_-_2_59"


def test_list_positions_script(capsys, tmp_path):
    from endgame_book.list_positions import main
    tex = tmp_path / "rook.tex"
    assert main(["--input", FIXTURES, "--material", "R v RB", "--show", "5", "--latex", str(tex)]) == 0
    out = capsys.readouterr().out
    assert "1 positions with a blunder in R v RB" in out and "3.Rd2? Bc5 4.Kg2 0-1" in out
    latex = tex.read_text(encoding="utf-8")
    assert "\\diagram[rook-knight-3w]{4k3/8/8/8/8/8/8/3R1Kb1 w - - 0 3}" in latex
    assert "\\moves{3.\\R d2? \\B c5 4.\\K g2}" in latex


def test_make_book_writes_only_what_is_needed_and_keeps_your_edits(tmp_path, monkeypatch):
    from endgame_book.band import Band
    from endgame_book.make import make
    monkeypatch.chdir(tmp_path)                                            # books/<band>/ is made here
    data = tmp_path / "input"
    shutil.copytree(FIXTURES, data)
    chapters = tmp_path / "chapters"
    monkeypatch.setattr("endgame_book.make.MIN_GAMES_FOR_CHAPTERS", 1)   # the sample has only a few games
    run = lambda **kw: make(str(data), Band(), str(chapters), min_games=1, **kw)
    part, appendix, listing, rook, rb = (chapters / n for n in (
        "where-the-mistakes-are.tex", "how-the-numbers-were-made.tex", "endgames.tex",
        "rook-endgames.tex", "rook-vs-rook-and-bishop.tex"))

    first = run()
    assert all(line.startswith("written") for line in first)
    assert {part.name, appendix.name, listing.name, rook.name, rb.name} <= {p.name for p in chapters.iterdir()}
    assert "% material: R v RB" in listing.read_text(encoding="utf-8")             # chapters in the order of study
    assert "\\chapter{Rook vs rook and bishop}" in rb.read_text(encoding="utf-8")
    assert all(line.startswith("kept") for line in run())                 # nothing changed: data not read

    newer = os.path.getmtime(part) + 10
    for pgn in data.rglob("*.pgn"):
        os.utime(pgn, (newer, newer))                                      # new games arrive
    appendix.write_text(appendix.read_text(encoding="utf-8") + "My own note.\n", encoding="utf-8")
    rook.write_text("% my comments\n", encoding="utf-8")
    lines = run()
    assert any(l.startswith("written") and "where-the-mistakes-are" in l for l in lines)   # refreshed
    assert any(l.startswith("kept") and "how-the-numbers" in l and "WARNING" in l for l in lines)
    assert "My own note." in appendix.read_text(encoding="utf-8")         # your edit stays
    assert rook.read_text(encoding="utf-8") == "% my comments\n"          # an endgame chapter is yours

    assert all(l.startswith("kept") for l in run(top=5, keep_statistics=True))          # kept on request
    assert any(l.startswith("written") and "where-the-mistakes-are" in l for l in run(top=5))  # settings changed

    rb.unlink()                                                            # a missing chapter is written again
    assert any(l.startswith("written") and rb.name in l for l in run(top=5))


def test_existing_chapter_positions_are_not_shown_again(tmp_path):
    from endgame_book.game_line import Shown
    chapter = tmp_path / "c.tex"
    chapter.write_text("\\diagram[a-b-59b]{6R1/8/p7/2r5/1k6/5K2/8/8 b - - 2 59}\n"
                       "\\moves{59...a5? 60.\\K e2 \\K b3}\n", encoding="utf-8")
    shown = Shown()
    shown.register_file(str(chapter))
    assert shown.labels == {"a-b-59b"}
    assert shown.positions["6R1/8/8/p1r5/8/1k6/4K3/8 w"] == "a-b-59b"           # reached after 60...Kb3


def test_mate_sign_is_escaped_for_latex():
    from endgame_book.latex import _mainline
    from endgame_book.reader import Move
    assert _mainline([(Move(1, 33, True, "Rh8#", None, {}), "")]) == "\\moves{33.\\R h8\\#}"


def test_board_cache_finds_every_diagram_once(tmp_path):
    from endgame_book import boards
    a, b = tmp_path / "a.tex", tmp_path / "b.tex"
    a.write_text("\\diagram[x]{8/8/8/4k3/8/8/4K3/8 w - - 0 1}\n\\diagram{6R1/8/p7/2r5/1k6/5K2/8/8 b - - 2 59}\n",
                 encoding="utf-8")
    b.write_text("\\diagram[y]{8/8/8/4k3/8/8/4K3/8 w - - 0 1}\n", encoding="utf-8")
    assert boards.positions_in([str(a), str(b)]) == ["8/8/8/4k3/8/8/4K3/8 w - - 0 1",
                                                     "6R1/8/p7/2r5/1k6/5K2/8/8 b - - 2 59"]
    page = boards._map_tex({"8/8/8/4k3/8/8/4K3/8 w - - 0 1": ("batch-1.pdf", 3)}, "output/boards")
    assert "\\csname eg@board@8/8/8/4k3/8/8/4K3/8 w - - 0 1\\endcsname{{output/boards/batch-1.pdf}{3}}" in page


def test_unchanged_file_keeps_its_date(tmp_path):
    from endgame_book.boards import _write_if_changed
    f = tmp_path / "m.tex"
    _write_if_changed(str(f), "x")
    os.utime(f, (1000, 1000))
    _write_if_changed(str(f), "x")
    assert os.path.getmtime(f) == 1000
    _write_if_changed(str(f), "y")
    assert os.path.getmtime(f) > 1000


def test_elo_band_rules_and_names():
    from endgame_book.band import Band
    game = {"white_elo": "1650", "black_elo": "1450"}
    assert not Band(None, 1599).ok(game) and Band(None, 1599, "average").ok(game)       # average 1550
    assert Band(1500, 1599, "average").ok(game) and not Band(1500, 1599).ok(game)
    assert not Band(1500).ok({"white_elo": "1600", "black_elo": ""})                   # rating missing
    assert Band().ok({"white_elo": "", "black_elo": ""})                                # no limits: every game
    assert Band(1500, 1599, "average").slug == "1500-1599-average"
    assert Band(2600).slug == "2600-plus-both" and Band(None, 1599, "average").slug == "upto-1599-average"
    assert Band(1500, 1599, "average").job == "Endgames-Elo-1500-1599-average"
    assert Band(None, 1599, "average").describe() == "Rated 1599 and below (average of both players)"


def test_no_endgame_chapters_for_a_band_without_enough_games(tmp_path, monkeypatch):
    from endgame_book.band import Band
    from endgame_book.make import make
    monkeypatch.chdir(tmp_path)
    data = tmp_path / "input"
    shutil.copytree(FIXTURES, data)
    lines = make(str(data), Band(1500, 1599, "average"), min_games=1)
    assert any(l.startswith("not yet") for l in lines)
    assert sorted(os.listdir(tmp_path / "books" / "1500-1599-average" / "chapters")) == [
        "endgames.tex", "how-the-numbers-were-made.tex", "where-the-mistakes-are.tex"]
