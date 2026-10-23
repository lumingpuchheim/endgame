"""python -m endgame_book [--input FOLDER] [--min-elo N] [options]

Reads the data once and writes Part I (chapters 1-3) and the appendix into
chapters/. The book itself is compiled by scripts/build_book.bat.
"""

import argparse
import logging
import sys

from .build import CHAPTERS, write_statistics


def main(argv=None) -> int:
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="python -m endgame_book",
                                     description="Write Part I and the appendix of the book from the data.")
    parser.add_argument("--input", default="input", help="folder with annotated PGN files or links to them (default: input)")
    parser.add_argument("--chapters", default=CHAPTERS, help=f"folder for the chapter files (default: {CHAPTERS})")
    parser.add_argument("--min-elo", type=int, help="only games where both players have at least this rating")
    parser.add_argument("--min-games", type=int, default=500, help="smallest number of games for a material to be ranked (default: 500)")
    parser.add_argument("--top", type=int, default=15, help="rows in the material charts (default: 15)")
    args = parser.parse_args(argv)
    try:
        write_statistics(args.input, args.chapters, args.min_elo, args.min_games, args.top)
    except (FileNotFoundError, ValueError) as exc:
        logging.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
