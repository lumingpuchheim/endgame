"""python -m endgame_report [--input FOLDER] [--out FOLDER] [options]"""

import argparse
import logging
import sys

from .build import build


def main(argv=None) -> int:
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="python -m endgame_report",
                                     description="Build the endgame report (HTML, LaTeX, PDF) in one run.")
    parser.add_argument("--input", default="input", help="folder with annotated PGN files or links to them (default: input)")
    parser.add_argument("--out", default="output", help="folder for the report files (default: output)")
    parser.add_argument("--name", default="report", help="file name without extension (default: report)")
    parser.add_argument("--min-elo", type=int, help="only games where both players have at least this rating")
    parser.add_argument("--min-games", type=int, default=500, help="smallest number of games for a material to be ranked (default: 500)")
    parser.add_argument("--top", type=int, default=25, help="rows in the material tables (default: 25)")
    parser.add_argument("--no-pdf", action="store_true", help="write HTML and LaTeX only")
    args = parser.parse_args(argv)
    try:
        build(args.input, args.out, args.name, args.min_elo, args.min_games, args.top, not args.no_pdf)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        logging.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
