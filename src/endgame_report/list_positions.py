"""List the positions where a blunder was made in one material, simplest first.

    python -m endgame_report.list_positions [--input FOLDER] [--min-elo N] [--material "R v R"] [--show N]

Prints how many positions there are for each number of pieces on the board, then the
first N positions with the game, the move and a Lichess link. Reads the same input
folder as the book; writes nothing.
"""

import argparse
import logging
import sys
from collections import Counter

from .collect import collect
from .latex import lichess_url
from .sections import positions
from .stats import _elo_ok


def main(argv=None) -> int:
    logging.basicConfig(level="WARNING", format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="python -m endgame_report.list_positions",
                                     description="Positions with a blunder in one material, simplest first.")
    parser.add_argument("--input", default="input", help="folder with annotated PGN files or links (default: input)")
    parser.add_argument("--min-elo", type=int, help="only games where both players have at least this rating")
    parser.add_argument("--material", default="R v R", help='material as the book writes it (default: "R v R")')
    parser.add_argument("--show", type=int, default=20, help="positions to list; 0 = none (default: 20)")
    args = parser.parse_args(argv)
    try:
        games, _segments, blunders, _counts = collect(args.input)
    except (FileNotFoundError, ValueError) as exc:
        logging.error("%s", exc)
        return 1
    kept = {g["game_id"] for g in games if _elo_ok(g, args.min_elo)}
    found, total = positions(games, blunders, kept, wanted=args.material)

    print(f"{len(kept):,} games, {total:,} positions with a blunder in {args.material}.\n")
    print("Pieces on the board (kings and pawns included)   Positions")
    for pieces, count in sorted(Counter(p.pieces for p in found).items()):
        print(f"{pieces:>8}{count:>45,}")
    if args.show:
        print(f"\nFirst {min(args.show, total)} positions:")
        for i, p in enumerate(found[: args.show], 1):
            b, g = p.blunder, p.game
            move = f"{b['move_number']}.{'' if b['mover'] == 'white' else '..'}{b['move']}"
            print(f"{i:>4}. {p.pieces} pieces  {g['white']} - {g['black']}, {g['event']} {g['date'][:4]}: "
                  f"{move} (best {b['best']})")
            print(f"      {lichess_url(b['fen'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
