"""python -m endgame_book [options]: everything in one run.

Reads the data once and writes
  chapters/where-the-mistakes-are.tex     Part I (chapters 1-3)
  chapters/how-the-numbers-were-made.tex  appendix
  chapters/rook-endgames.tex              rook positions (replaced on every run)
scripts/make_book.bat then compiles book.tex to output/book.pdf.
"""

import argparse
import logging
import os
import sys

from .build import APPENDIX, CHAPTERS, PART_ONE, ROOK_CHAPTER, write_positions, write_statistics
from .collect import collect


def main(argv=None) -> int:
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="python -m endgame_book",
                                     description="Write all chapters of the book from the data.")
    parser.add_argument("--input", default="input", help="folder with annotated PGN files or links to them (default: input)")
    parser.add_argument("--chapters", default=CHAPTERS, help=f"folder for the chapter files (default: {CHAPTERS})")
    parser.add_argument("--min-elo", type=int, help="only games where both players have at least this rating")
    parser.add_argument("--min-games", type=int, default=500, help="smallest number of games for an endgame to be ranked (default: 500)")
    parser.add_argument("--top", type=int, default=15, help="rows in the charts (default: 15)")
    parser.add_argument("--show", type=int, default=50, help="rook positions in all (default: 50)")
    parser.add_argument("--per-section", type=int, metavar="N", help="at most N rook positions for each pawn balance")
    args = parser.parse_args(argv)
    try:
        games, segments, blunders, _counts = collect(args.input)
        written = write_statistics(games, segments, blunders, args.chapters, args.min_elo, args.min_games, args.top)
        rook = os.path.join(args.chapters, ROOK_CHAPTER)
        entries = write_positions(args.input, games, blunders, rook, args.min_elo, args.show, args.per_section,
                                  echo=False)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        logging.error("%s", exc)
        return 1
    print("\nWritten:")
    for path in written:
        print(f"  {path}")
    print(f"  {rook} ({len(entries)} positions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
