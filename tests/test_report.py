import os
import re
import shutil

import pytest

from endgame_report.build import build
from endgame_report.collect import collect
from endgame_report.reader import find_files, iter_games
from endgame_report.categories import CATEGORIES, category
from endgame_report.stats import is_real_blunder, lasting_segments, material, summarize

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


def test_one_run_writes_exactly_three_files(tmp_path):
    out = tmp_path / "out"
    written = build(FIXTURES, str(out), min_games=1, pdf=bool(shutil.which("pdflatex")))
    expected = {"report.html", "report.tex"} | ({"report.pdf"} if shutil.which("pdflatex") else set())
    assert set(os.listdir(out)) == expected                          # no images, no LaTeX leftovers
    html = open(written["html"], encoding="utf-8").read()
    assert "<img" not in html and "<svg" not in html and "R v RB" in html
    tex = open(written["tex"], encoding="utf-8").read()
    assert "\\addplot" in tex and "includegraphics" not in tex


@pytest.mark.parametrize("signature,kind,expected", [
    ("-", "pawn", "pawns"), ("R-", "piece_vs_pawns", "pieces_vs_pawns"), ("-BN", "piece_vs_pawns", "pieces_vs_pawns"),
    ("Q-Q", "queen", "q_v_q"), ("QR-QB", "mixed", "queens_equal"), ("Q-QR", "mixed", "queens_unequal"),
    ("QR-RR", "mixed", "queen_vs_none"), ("R-R", "rook", "r_v_r"), ("RR-RR", "mixed", "rr_v_rr"),
    ("RN-RB", "mixed", "rm_v_rm"), ("RRB-RRN", "mixed", "rrm_v_rrm"), ("RBN-RBB", "mixed", "rmm_v_rmm"),
    ("R-RB", "mixed", "rooks_unequal"), ("RB-RR", "mixed", "rooks_unequal"), ("RB-BN", "mixed", "rook_vs_minors"),
    ("B-B", "bishop_same", "b_v_b_same"), ("B-B", "bishop_opposite", "b_v_b_opposite"), ("N-N", "knight", "n_v_n"),
    ("N-B", "bishop_knight", "b_v_n"), ("BN-B", "mixed", "minors_more"), ("RRR-RRR", "mixed", "other"),
])
def test_categories(signature, kind, expected):
    assert category(signature, kind) == expected
    assert category("-".join(reversed(signature.split("-"))), kind) == expected   # colour-neutral


def test_every_category_has_a_rule():
    keys = [c[0] for c in CATEGORIES]
    assert len(keys) == len(set(keys)) and all(rule and examples for _, _, rule, examples in CATEGORIES)


def test_exchange_in_progress_counts_as_the_material_before():
    segs = [{"order": "0", "moves": "6"},     # RB v RB stands for 6 moves
            {"order": "1", "moves": "1"},     # bishop taken ...
            {"order": "2", "moves": "9"}]     # ... and retaken: R v R
    assert lasting_segments(segs) == {0: 0, 1: 0, 2: 2}
    assert lasting_segments([{"order": "0", "moves": "1"}, {"order": "1", "moves": "4"}]) == {0: 1, 1: 1}
