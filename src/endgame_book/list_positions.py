"""List the positions where a blunder was made in one material, simplest first.

    python -m endgame_book.list_positions [--input FOLDER] [--min-elo N] [--material "R v R"]
                                            [--show N] [--latex FILE]

Prints how many positions there are for each number of pieces on the board, then the
first N positions with the game, a Lichess link and the rest of the game. With --latex,
the same positions are also written to FILE as LaTeX (diagram and moves, the same text
the book uses), ready to paste into book.tex. Reads the same input folder as the book.
"""

import argparse
import logging
import os
import sys
from collections import Counter

from .build import position_entries
from .collect import collect
from .game_line import plain_text
from .latex import lichess_url, positions_latex
from .sections import pawn_split
from .texts import pawns_title
from .sections import positions
from .stats import _elo_ok


def main(argv=None) -> int:
    logging.basicConfig(level="WARNING", format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="python -m endgame_book.list_positions",
                                     description="Positions with a blunder in one material, simplest first.")
    parser.add_argument("--input", default="input", help="folder with annotated PGN files or links (default: input)")
    parser.add_argument("--min-elo", type=int, help="only games where both players have at least this rating")
    parser.add_argument("--material", default="R v R", help='material as the book writes it (default: "R v R")')
    parser.add_argument("--show", type=int, default=20, help="positions to list in all; 0 = none (default: 20)")
    parser.add_argument("--per-section", type=int, metavar="N",
                        help="at most N positions for each pawn balance (e.g. rook and two pawns vs rook)")
    parser.add_argument("--latex", metavar="FILE", help="also write the listed positions as LaTeX to FILE")
    parser.add_argument("--overwrite", action="store_true", help="replace FILE if it exists")
    parser.add_argument("--notes", default="notes", help="folder with your comments (default: notes)")
    args = parser.parse_args(argv)
    try:
        games, _segments, blunders, _counts = collect(args.input)
    except (FileNotFoundError, ValueError) as exc:
        logging.error("%s", exc)
        return 1
    try:
        return _run(args, games, blunders)
    except RuntimeError as exc:
        logging.error("%s", exc)
        return 1


def _run(args, games, blunders) -> int:
    kept = {g["game_id"] for g in games if _elo_ok(g, args.min_elo)}
    found, total = positions(games, blunders, kept, wanted=args.material)

    print(f"{len(kept):,} games, {total:,} positions with a blunder in {args.material}.\n")
    counts = Counter(pawn_split(p.blunder["fen"]) for p in found)
    print(f"{'Positions':>9}  Pawn balance, simplest first")
    for split in dict.fromkeys(pawn_split(p.blunder["fen"]) for p in found):
        print(f"{counts[split]:>9,}  {pawns_title(split)}")
    if not args.show:
        return 0
    if args.latex and os.path.exists(args.latex) and not args.overwrite:
        logging.error("%s exists; add --overwrite to replace it (your comments in it would be lost)", args.latex)
        return 1
    entries = position_entries(args.input, found, args.notes, args.show, args.per_section)
    print(f"\nThe {len(entries)} simplest positions (a later mistake in a game already listed is left out):")
    for i, (p, items) in enumerate(entries, 1):
        g = p.game
        print(f"\n{i:>4}. {p.pieces} pieces, {'White' if p.blunder['mover'] == 'white' else 'Black'} to move. "
              f"{g['white']} - {g['black']}, {g['event']} {g['date'][:4]}")
        print(f"      {lichess_url(p.blunder['fen'])}")
        print(f"      {plain_text(items)}")
    if args.latex:
        with open(args.latex, "w", encoding="utf-8") as handle:
            handle.write(positions_latex(entries))
        print(f"\nLaTeX for these {len(entries)} positions written to {args.latex}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
