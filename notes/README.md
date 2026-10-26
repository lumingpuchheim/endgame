# Notes

Hand-written comments for the example games, in LaTeX. They are put into
the book next to the moves they belong to. A note is found by the position
it starts from, not by the game, so the same note serves every game that
reaches that position.

Each note starts with a line

    @ <FEN> | <move>

- `<FEN>`: the position before the move. Only the board and the side to move
  are compared; castling, en passant and move counters are ignored.
- `<move>`: the move played in that position, in the form the book prints
  it, with its mark: `a5?`, `Ke2!`, `Re5!!`. The mark replaces the
  automatic one. Write `start` instead of a move for a comment under the first
  diagram, and `end` for a comment under the final position.

Every position in a generated chapter has a line `% note: @ <FEN> | <move>?` just above it:
copy it here, without the `% note: `, and write your comment below it. A position you comment on
always stays in its chapter, even when the chapter is written again with new data.

To leave a position out of the book, write `skip` as the move: `@ <FEN> | skip`, with no comment.
The next position from the data takes its place, and it is never used as an exercise either.

The lines after it, up to the next `@` line, are the comment. A blank line starts a new
paragraph, as everywhere in LaTeX; blank lines before the next `@` line are ignored. Lines starting
with `%` are ignored.

Write pieces as chess figures with `\K`, `\Q`, `\R`, `\B`, `\N` followed by a
space, for example `59...\R e5!` or `e8=\Q`. The moves of the game itself are
converted by the program.
