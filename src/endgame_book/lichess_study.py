"""Write random complicated positions of one material as PGN, ready to import into a Lichess study.

    python -m endgame_book.lichess_study --out FILE [--input FOLDER] [--min-elo N] [--max-elo N]
                                         [--elo-rule both|average] [--material "R v R"]
                                         [--count 32] [--min-pawns 3] [--seed 1] [--no-moves]

Picks positions where a real blunder was made, with at least --min-pawns pawns on each side,
at most one position per game, at random (the same --seed gives the same positions). Each
position becomes one game in FILE: it starts at the position before the mistake and, unless
--no-moves, continues with the moves played, the mistake marked with "?" and Stockfish's
better move in a comment. In a Lichess study, "Add chapter" -> "PGN" turns every game into a
chapter; one import takes up to 32 games, so with more than 32 positions FILE is split into
FILE, FILE-2, FILE-3, ...
"""

import argparse
import logging
import os
import random
import sys
from typing import List

from .reader import find_files
from .collect import collect
from .compile import add_band_options, band_from
from .reader import read_moves
from .sections import Position, pawn_split, positions
from .texts import pawns_title

PER_IMPORT = 32


def complicated(pos: Position, min_pawns: int) -> bool:
    (_, more), (_, fewer) = pawn_split(pos.blunder["fen"])
    return fewer >= min_pawns


def pick(found: List[Position], count: int, min_pawns: int, seed: int) -> List[Position]:
    """`count` random positions with at least `min_pawns` pawns on each side, one per game."""
    pool = [p for p in found if complicated(p, min_pawns)]
    random.Random(seed).shuffle(pool)
    chosen, games = [], set()
    for p in pool:
        if p.game["game_id"] in games:
            continue
        games.add(p.game["game_id"])
        chosen.append(p)
        if len(chosen) == count:
            break
    return chosen


def game_pgn(pos: Position, path: str, with_moves: bool) -> str:
    """One position as a PGN game that starts at the position before the mistake."""
    import chess
    import chess.pgn

    g, b = pos.game, pos.blunder
    game = chess.pgn.Game()
    game.setup(chess.Board(b["fen"]))
    h = game.headers
    h["Event"] = g.get("event", "?") or "?"
    h["Date"] = (g.get("date") or "????.??.??").replace("-", ".")
    h["White"] = g.get("white", "?") or "?"
    h["Black"] = g.get("black", "?") or "?"
    h["Result"] = g.get("result", "*") or "*"
    for color in ("White", "Black"):
        elo = g.get(f"{color.lower()}_elo")
        if elo:
            h[f"{color}Elo"] = str(elo)
    h["Orientation"] = b["mover"]          # see the board from the side that went wrong
    mover = "White" if b["mover"] == "white" else "Black"
    game.comment = f"{mover} to move. {pawns_title(pawn_split(b['fen']))}."
    if not with_moves:
        return str(game)
    _headers, moves = read_moves(path, g["game_id"])
    node, board = game, chess.Board(b["fen"])
    for m in (m for m in moves if m.ply >= int(b["ply"])):
        move = board.parse_san(m.san)
        node = node.add_variation(move)
        board.push(move)
        if m.blunder and m.blunder.get("best") and m.blunder["best"] != m.san \
                and m.blunder.get("holding") not in ("", "0", None):
            node.nags.add(chess.pgn.NAG_MISTAKE)
            node.comment = f"Stockfish prefers {m.blunder['best']}."
    return str(game)


def main(argv=None) -> int:
    logging.basicConfig(level="WARNING", format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="python -m endgame_book.lichess_study",
                                     description="Random complicated positions as PGN for a Lichess study.")
    parser.add_argument("--out", required=True, metavar="FILE", help="the PGN file to write")
    parser.add_argument("--input", default="input", help="folder with annotated PGN files or links (default: input)")
    add_band_options(parser)
    parser.add_argument("--material", default="R v R", help='material as the book writes it (default: "R v R")')
    parser.add_argument("--count", type=int, default=PER_IMPORT, help=f"positions (default: {PER_IMPORT})")
    parser.add_argument("--min-pawns", type=int, default=3, help="at least this many pawns on each side (default: 3)")
    parser.add_argument("--seed", type=int, default=1, help="another number gives other positions (default: 1)")
    parser.add_argument("--no-moves", action="store_true", help="only the position, without the moves played")
    args = parser.parse_args(argv)
    try:
        games, _segments, blunders, _counts = collect(args.input)
    except (FileNotFoundError, ValueError) as exc:
        logging.error("%s", exc)
        return 1
    band = band_from(args)
    kept = {g["game_id"] for g in games if band.ok(g)}
    found, total = positions(games, blunders, kept, wanted=args.material)
    chosen = pick(found, args.count, args.min_pawns, args.seed)
    eligible = sum(1 for p in found if complicated(p, args.min_pawns))
    print(f"{len(kept):,} games, {total:,} positions with a blunder in {args.material}, "
          f"{eligible:,} of them with at least {args.min_pawns} pawns on each side.")
    if not chosen:
        print("No position to write.")
        return 1
    paths = {os.path.basename(p): p for p in find_files(args.input)}
    texts = [game_pgn(p, paths[p.game["source"]], not args.no_moves) for p in chosen]
    stem, ext = os.path.splitext(args.out)
    written = []
    for i in range(0, len(texts), PER_IMPORT):
        name = args.out if i == 0 else f"{stem}-{i // PER_IMPORT + 1}{ext or '.pgn'}"
        os.makedirs(os.path.dirname(os.path.abspath(name)), exist_ok=True)
        with open(name, "w", encoding="utf-8") as handle:
            handle.write("\n\n".join(texts[i:i + PER_IMPORT]) + "\n")
        written.append(name)
    print(f"{len(chosen)} positions written to {', '.join(written)} (seed {args.seed}).")
    print('In Lichess: open or create a study, "Add chapter" -> "PGN", paste one file. Each game becomes a chapter.')
    return 0


if __name__ == "__main__":
    sys.exit(main())
