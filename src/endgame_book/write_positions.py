"""Write the simplest positions of one material, with the rest of each game, to a LaTeX file.

    python -m endgame_book.write_positions FILE [--min-elo N] [--show N] [--per-section N]
                                                [--material "R v R"] [--input FOLDER] [--overwrite]

Also prints how many positions each pawn balance has and every position written.
"""

import argparse
import logging
import os
import sys

from .build import write_positions
from .collect import collect


def main(argv=None) -> int:
    logging.basicConfig(level="WARNING", format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="python -m endgame_book.write_positions",
                                     description="Write positions with a blunder, simplest first, to a LaTeX file.")
    parser.add_argument("file", help="the LaTeX file to write, e.g. chapters\\rook-draft.tex")
    parser.add_argument("--input", default="input", help="folder with annotated PGN files or links (default: input)")
    parser.add_argument("--min-elo", type=int, help="only games where both players have at least this rating")
    parser.add_argument("--material", default="R v R", help='material as the book writes it (default: "R v R")')
    parser.add_argument("--show", type=int, default=20, help="positions in all (default: 20)")
    parser.add_argument("--per-section", type=int, metavar="N",
                        help="at most N positions for each pawn balance (e.g. rook and two pawns vs rook)")
    parser.add_argument("--overwrite", action="store_true", help="replace the file if it exists")
    parser.add_argument("--notes", default="notes", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if os.path.exists(args.file) and not args.overwrite:
        logging.error("%s exists; add --overwrite to replace it (your comments in it would be lost)", args.file)
        return 1
    try:
        games, _segments, blunders, _counts = collect(args.input)
        entries = write_positions(args.input, games, blunders, args.file, args.min_elo, args.show,
                                  args.per_section, args.material, args.notes)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        logging.error("%s", exc)
        return 1
    print(f"\nWritten: {args.file} ({len(entries)} positions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
