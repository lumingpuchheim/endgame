# Where Grandmasters Go Wrong in the Endgame

An endgame book built from engine-annotated tournament games. The idea: find
where strong players make the most mistakes, and study those endgames first.

1. **Which endgames are the most common?**
   For each material (e.g. `RB v RN`), how many of 100 games reach it.
2. **Which endgames are tricky?**
   For each material reached in at least 500 games, blunders per 100 games
   that reached it, with the number of games behind every value.
3. **Which endgames cause the most blunders overall?**
   Blunders made in each material per 100 games played: how often it happens
   times how often it goes wrong. These are the endgames worth studying first.
4. **Rook endings:** positions where a player blundered, simplest first, each
   with the rest of the game. Your comments go in between.

The book reads annotated PGN files made by `chessticize-worker`
(`python -m chessticize_worker.twic annotate`). It needs nothing else from
that project: the file format is described in
[docs/input-format.md](docs/input-format.md).

## The input folder

The book reads **one folder**, `input/` by default, including everything
reached through links inside it. The annotated files themselves stay where
they are made; `input/` only holds links to them. Nothing in `input/` is
committed to git.

### Creating the links

**Windows** (Command Prompt, in this repository folder). A folder link
("junction") needs no administrator rights:

```
mklink /J input\twic-annotated C:\Users\user\workspace\chessticize-worker\data\twic\annotated
```

Create the link in Windows itself (Command Prompt, as above). A link made from
WSL or another Linux shell looks fine there but cannot be followed by Windows
programs, and the book then finds no files.

The link shows up as a folder `input\twic-annotated`. Files added to the
annotated folder later appear through it automatically.

To remove the link (this removes only the link, not the files it points to):

```
rmdir input\twic-annotated
```

**Linux / macOS**:

```
ln -s /path/to/chessticize-worker/data/twic/annotated input/twic-annotated
rm input/twic-annotated          # removes the link only
```

Several links are fine, for example one per annotation run. All files
reachable from `input/` are read, and a game that appears twice (same
`GameId`) is counted once. All linked files must use the same endgame rule and
engine depth; the book stops with a message if they don't.

To check what the book will read, list the folder through the link:
`dir input\twic-annotated` (Windows) or `ls input/twic-annotated`.

## The book's files

| File | What it is | Written by |
|---|---|---|
| `book.tex` | The book: cover, contents, parts, the chapter for each endgame | you (in git) |
| `endgame.sty` | Look of the book and its macros (`\bookcover`, `\xref`, `\game`, `\diagram`, `\moves`, `\seen`, `\K \Q \R \B \N`) | in git |
| `chapters\introduction.tex` | How to use this book | you (in git) |
| `chapters\where-the-mistakes-are.tex` | Part I: chapters 1-3 with the charts | `make_book.bat` |
| `chapters\rook-endgames.tex` | Chapter 4: rook positions by pawn balance | `make_book.bat`, replaced every run |
| `chapters\how-the-numbers-were-made.tex` | Appendix: the data and the words used | `make_book.bat` |
| `output\book.pdf` | The compiled book | `make_book.bat` |

## Two commands

**Everything in one run:**

```
scripts\make_book.bat --min-elo 2600 --show 60 --per-section 20
```

Reads the data, writes the statistics (Part I, appendix), writes the rook
positions to `chapters\rook-endgames.tex`, compiles `output\book.pdf`, and
names every file it wrote. `chapters\rook-endgames.tex` is replaced on every
run, so write your comments in a file of your own (see below) and include that
in `book.tex`.

| Option | Default | Meaning |
|---|---|---|
| `--min-elo N` | none | Only games where both players are rated N or more |
| `--show N` | 50 | Rook positions in all, simplest first |
| `--per-section N` | none | At most N rook positions of each pawn balance (rook and two pawns vs rook, ...) |
| `--input FOLDER` | `input` | Folder with annotated PGN files or links to them |
| `--chapters FOLDER` | `chapters` | Where the chapter files go |
| `--min-games N` | 500 | Smallest number of games for an endgame to be ranked in chapter 2 |
| `--top N` | 15 | Rows in the charts |

**Positions into a file you name:**

```
scripts\write_positions.bat chapters\rook-draft.tex --min-elo 2600 --show 60 --per-section 20
```

Writes the positions, each with its diagram and the rest of the game, to the
file you give, and prints how many positions each pawn balance has and every
position written. An existing file is kept unless you add `--overwrite`.
Options as above, plus `--material "R v RB"` for another material.

To use the file in the book, put `\input{chapters/rook-draft.tex}` in
`book.tex` (instead of, or next to, `chapters/rook-endgames.tex`).

Each position looks like this; write your comments between the lines:

```
\game{Wang Hao (2737)}{Mamedyarov (2764)}{SportAccord Blitz Men 2012}
\diagram[wanghao-mamedyarov-59b]{6R1/8/p7/2r5/1k6/5K2/8/8 b - - 2 59}

\moves{59...a5? 60.\K e2 \K b3 61.\K d2}
0-1\par
```

To point to another place, write `\xref{Chapter}{ch:where-to-start}` or
`\xref{diagram}{wanghao-mamedyarov-59b}`: the word and the number are one
link. Labels: `part:mistakes`, `part:endgames`, `ch:meet`, `ch:go-wrong`,
`ch:where-to-start`, `ch:rook-vs-rook`, `app:numbers`, and the label in
each `\diagram[...]`.

Paths are relative to this repository folder.

## Requirements

- Python 3.8 or newer with python-chess (`py -m pip install chess`; already there if
  chessticize-worker runs with the same Python). It replays the games for the positions.
- For the PDF: `pdflatex` with the class `memoir` and the packages `pgfplots`, `tikz`, `chessboard`, `hyperref`, `microtype`,
  `array`, `geometry`, `xcolor`, `lmodern` (MiKTeX installs missing packages
  on first use; on TeX Live, `chessboard` is in `texlive-games`).

## Tests

```
PYTHONPATH=src python -m pytest tests
```

The tests use a small hand-made sample in `tests/fixtures/`, not the real data.
