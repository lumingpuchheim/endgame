# Notes

Hand-written comments for the example games, in LaTeX. They are put into
the report next to the moves they belong to. A note is found by the position
it starts from, not by the game, so the same note serves every game that
reaches that position.

Each note starts with a line

    @ <FEN> | <move>

- `<FEN>`: the position before the move. Only the board and the side to move
  are compared; castling, en passant and move counters are ignored.
- `<move>`: the move played in that position, in the form the report prints
  it, with its mark: `a5?`, `Ke2!`, `Re5!!`. The mark replaces the
  automatic one. Write `start` instead of a move for a comment under the first
  diagram, and `end` for a comment under the final position.

The lines after it, up to the next `@` line, are the comment. Lines starting
with `%` are ignored.
