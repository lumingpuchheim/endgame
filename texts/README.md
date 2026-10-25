# Your own texts

Text that is not about one position: a section of theory, an introduction to a pawn balance.
make_book never writes here; the generated chapters include these files if they exist.

- `texts/<chapter>.tex`: after the chapter's opening, before the positions,
  e.g. `texts/rook-endgames.tex`.
- `texts/<chapter>/<section>.tex`: at the start of that section,
  e.g. `texts/rook-endgames/rook-and-two-pawns-vs-rook.tex`.
- `books/<band>/texts/...` with the same names: used instead, for that band only.

The chapter and section names are the file names make_book uses; each generated chapter shows
them in its `\yourtext{...}` lines.
