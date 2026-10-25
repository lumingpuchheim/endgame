"""python -m endgame_book [options]: the whole book in one run (scripts/make_book.bat).
Brings the chapter files up to date (make.py), then compiles the book (compile.py)."""

import argparse
import logging
import sys

from .compile import add_band_options, band_from, compile_book
from .make import make


def main(argv=None) -> int:
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="python -m endgame_book",
                                     description="Bring the chapters of the book up to date.")
    parser.add_argument("--input", default="input", help="folder with annotated PGN files or links to them (default: input)")
    add_band_options(parser)
    parser.add_argument("--chapters", help="folder for the chapter files (default: books/<band>/chapters)")
    parser.add_argument("--min-games", type=int, default=500, help="smallest number of games for an endgame to be ranked (default: 500)")
    parser.add_argument("--top", type=int, default=15, help="rows in the charts (default: 15)")
    parser.add_argument("--always", action="append", metavar="MATERIAL",
                        help='an endgame chapter to include even if the data does not rank it, e.g. '
                             '"B v B opposite" (repeatable; default: "B v B opposite"; "none" for none)')
    parser.add_argument("--endgames", type=int, default=15,
                        help="endgame chapters, in the order of study; each side at most two pieces (default: 15)")
    parser.add_argument("--show", type=int, default=30, help="positions in a new endgame chapter (default: 30)")
    parser.add_argument("--per-section", type=int, default=10, metavar="N",
                        help="at most N positions of each pawn balance in a new endgame chapter (default: 10)")
    parser.add_argument("--exercises", type=int, default=10, metavar="N",
                        help="exercises after each pawn balance in a new endgame chapter (default: 10)")
    parser.add_argument("--only", metavar="CHAPTER",
                        help="typeset only this chapter into books/<band>/draft.pdf (e.g. rook-endgames); fast")
    parser.add_argument("--force", action="store_true", help="compile even if nothing changed")
    parser.add_argument("--keep-statistics", action="store_true",
                        help="keep the statistics files as they are, even if the data has changed")
    args = parser.parse_args(argv)
    band = band_from(args)
    print(f"Book: {band.describe()} -> {band.folder}")
    if args.only:                                   # a quick draft: the chapter files stay as they are
        return compile_book(args.only, args.force, band)
    try:
        report = make(args.input, band, args.chapters, args.min_games, args.top, args.show, args.per_section,
                      args.keep_statistics, args.endgames, args.exercises,
                      tuple(a for a in (args.always or ["B v B opposite"]) if a != "none"))
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        logging.error("%s", exc)
        return 1
    print()
    for line in report:
        print(line)
    print()
    return compile_book(args.only, args.force, band)


if __name__ == "__main__":
    sys.exit(main())
