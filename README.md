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
| `chapters\where-the-mistakes-are.tex` | Part I: chapters 1-3 with the charts | `make_book.bat`; kept once you edit it |
| `chapters\endgames.tex` | The list of endgame chapters, in the order of study | `make_book.bat`; kept once you edit it |
| `chapters\<endgame>.tex` | One chapter per endgame (`rook-endgames.tex`, `bishop-vs-knight.tex`, ...): positions, games, your comments | `make_book.bat` once, then you |
| `chapters\how-the-numbers-were-made.tex` | Appendix: the data and the words used | `make_book.bat`; kept once you edit it |
| `output\book.pdf` | The compiled book | `make_book.bat` |

## One command for the book

```
scripts\make_book.bat --min-elo 2600
```

Every run brings the chapter files up to date and compiles `output\book.pdf`.
It prints what it did with each chapter file:

- **Statistics** (Part I, appendix) are written when the file is missing, or
  when the data, the settings (`--min-elo`, `--min-games`, `--top`) or the
  program changed since it was written. Otherwise they are kept, and the data is not read at all
  (a run then takes seconds). Each generated file carries a check line at the
  top; if you edit the file, the check no longer matches and `make_book` keeps
  your version. When the data has changed since, it prints a WARNING. To get
  fresh numbers, rename or delete the file and run again.
- **Endgame chapters**: the first `--endgames N` endgames (default 15) of
  chapter 3's order in which each side has at most two pieces besides king and
  pawns get a chapter each; the order is in `chapters\endgames.tex`. A chapter
  file is written only if it does not exist yet, with the simplest `--show N`
  positions (default 30), at most `--per-section N` (default 10) of each pawn
  balance. After that it is yours and never replaced. Positions already shown
  in an earlier chapter are not repeated.
- **The book** is compiled, doing only the work that is needed:
  - every chess board is drawn once and kept in `output\boards`; only new
    positions are drawn (drawing all boards takes about a minute, placing them
    in the book a few seconds);
  - if nothing changed since the last `output\book.pdf`, nothing is compiled
    (`--force` compiles anyway);
  - the glossary is rebuilt only when it changed, and pdflatex runs again only
    when references moved; LaTeX's helper files stay in `output\` for that;
  - the window shows each chapter as pdflatex reaches it, and the time of each run.

For quick work on one chapter:

```
scripts\make_book.bat --only rook-endgames
```

typesets only that chapter into `output\draft.pdf` in a few seconds (the
chapter files are not updated; references to other chapters come from the last
full build).

The look of a board is set in `board-style.tex`. After changing it, delete
`output\boards` so that all boards are drawn again.

While the annotation run is still adding games, the data changes all the time,
so the statistics are refreshed on every run until it is finished. Add
`--keep-statistics` to skip that.

| Option | Default | Meaning |
|---|---|---|
| `--min-elo N` | none | Only games where both players are rated N or more |
| `--keep-statistics` | | Keep the statistics files as they are, even if the data has changed |
| `--only CHAPTER` | | Typeset only this chapter into `output\draft.pdf` |
| `--force` | | Compile even if nothing changed |
| `--endgames N` | 15 | Endgame chapters, in the order of study |
| `--show N` | 30 | Positions in a new endgame chapter |
| `--per-section N` | 10 | At most N of each pawn balance in a new endgame chapter |
| `--input FOLDER` | `input` | Folder with annotated PGN files or links to them |
| `--chapters FOLDER` | `chapters` | Where the chapter files are |
| `--min-games N` | 500 | Smallest number of games for an endgame to be ranked in chapter 2 |
| `--top N` | 15 | Rows in the charts |

## Positions into a file you name

```
scripts\list_positions.bat --min-elo 2600 --show 60 --per-section 20 --latex chapters\rook-draft.tex
```

For positions of your own choice, in a file you name. To put the file in the
book, add `\input{chapters/rook-draft.tex}` to `book.tex`.

Prints how many positions with a blunder there are in rook vs rook endings for
each number of pieces on the board, then the simplest positions, each with the
game, a Lichess link and the rest of the game (`59...a5? 60.Ke2 Kb3 61.Kd2 0-1`).
With `--latex FILE` the same positions are written to FILE as LaTeX, one
section per pawn balance, and the book is compiled right after
(`output\book.pdf`), so one command shows the result. If FILE
exists, it is kept unless you add `--overwrite` (your comments in it would be
lost). Options: `--per-section N` for at most N positions of each pawn balance
(`--show 60 --per-section 20` gives 20 each of rook and pawn vs rook, rook and
two pawns vs rook, rook and pawn vs rook and pawn), `--material "R v RB"` for
another material (bishop endings: `"B v B same"` or `"B v B opposite"`), `--show N` for the total
number of positions (0 = only the counts), `--input FOLDER`.

Each position in the LaTeX file looks like this; write your comments between
the lines, pieces as `\R e5`:

```
\game{Wang Hao (2737)}{Mamedyarov (2764)}{SportAccord Blitz Men 2012}
\diagram[wanghao-mamedyarov-59b]{6R1/8/p7/2r5/1k6/5K2/8/8 b - - 2 59}

\moves{59...a5? 60.\K e2 \K b3 61.\K d2}
0-1\par
```

To point the reader to another place, write `\xref{Chapter}{ch:where-to-start}`
or `\xref{diagram}{wanghao-mamedyarov-59b}`: the word and the number are one
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
