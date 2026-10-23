# Input format

Annotated PGN files written by `chessticize-worker twic 0.2.0`
(`Annotator` header). The book checks this header and stops on any other
value, so a future format change cannot be misread silently.

Only these parts are used.

## Headers (every game)

| Header | Example | Used for |
|---|---|---|
| `GameId` | `9f3a1c0b2d4e` | Counting each game once |
| `White`, `Black`, `WhiteElo`, `BlackElo` | | `--min-elo`, blunder attribution |
| `Event`, `Date`, `Result` | | Listed in the data |
| `TimeControlClass`, `TimeControlSource` | `classical`, `tag` | Carried along |
| `EgStartPly` | `60` or `-` | `-` = the game never reached an endgame |
| `EgStartGroup` | `equal` | Who was better when the endgame started |
| `EndgameRule` | `max 3 pieces per side` | Must be the same for all input files |
| `AnnotationDepth` | `15` | Must be the same for all input files |
| `Annotator` | `chessticize-worker twic 0.2.0` | Format check |

Games without an endgame are still in the files (headers and moves only);
they count in "N of 100 games".

## Move comments (from the endgame start on)

```
{ [%eval 0.35] }                                   engine score, White's view, pawns; #3 / #-3 = mate
{ [%egstart RN-RB mixed] RN-RB ending starts }     a material segment starts after this move
{ [%egend RN-RB mixed] RN-RB ending ends }         it ends after this move (or the game ends)
{ [%fen <FEN>] }                                   the position before the next move, which is a blunder
30. Nc4 $4 { [%blunder equal>losing best=Rf1 bestEval=-0.03 holding=2] }
```

A move after `egstart` and up to its `egend` belongs to that segment. The
move carrying `egend`/`egstart` itself belongs to the segment that was in
force before it.

Signatures are `White pieces - Black pieces` in the order Q, R, B, N
(`RN-RB`, `R-` = rook against pawns, `-` = pawns only). The book makes them
colour-neutral (`RB v RN`).
