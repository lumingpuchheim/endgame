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

The report reads **one folder**, `input/` by default, including everything
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
programs, and the report then finds no files.

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
engine depth; the report stops with a message if they don't.

To check what the report will read, list the folder through the link:
`dir input\twic-annotated` (Windows) or `ls input/twic-annotated`.

## The book's files

| File | What it is | Written by |
|---|---|---|
| `report.tex` | The book: title, chapter headings, `\input` of the chapters | you (in git) |
| `endgame.sty` | Layout and chess macros (`\game`, `\diagram`, `\moves`, `\seen`, `\K \Q \R \B \N`) | in git |
| `chapters\statistics.tex` | Introduction and chapters 1-3 | `update_statistics.bat` |
| `chapters\rook-endgames.tex` | Chapter 4: positions, games, your comments | `list_positions.bat` once, then you |
| `output\report.pdf` | The compiled book | `build_report.bat` |

## Three commands

**1. Statistics** - only when the data has changed (it reads all games):

```
scripts\update_statistics.bat --min-elo 2600
```

Writes `chapters\statistics.tex`; the next run replaces it. Options:

| Option | Default | Meaning |
|---|---|---|
| `--input FOLDER` | `input` | Folder with annotated PGN files or links to them |
| `--out FILE` | `chapters\statistics.tex` | Where the chapter goes |
| `--min-elo N` | none | Only games where both players are rated N or more |
| `--min-games N` | 500 | Smallest number of games for a material to be ranked as tricky |
| `--top N` | 25 | Rows in the material charts |

**2. Positions** - to start a chapter, or to look at the data:

```
scripts\list_positions.bat --min-elo 2600 --show 50 --latex chapters\rook-endgames.tex
```

Prints how many positions with a blunder there are in rook vs rook endings for
each number of pieces on the board, then the simplest positions, each with the
game, a Lichess link and the rest of the game (`59...a5? 60.Ke2 Kb3 61.Kd2 0-1`).
With `--latex FILE` the same positions are written to FILE as LaTeX. If FILE
exists, it is kept unless you add `--overwrite` (your comments in it would be
lost). Options: `--material "R v RB"` for another material, `--show N` for the
number of positions (0 = only the counts), `--input FOLDER`.

Each position in the LaTeX file looks like this; write your comments between
the lines, pieces as `\R e5`:

```
\game{Wang Hao (2737)}{Mamedyarov (2764)}{SportAccord Blitz Men 2012}
\diagram[wanghao-mamedyarov-59b]{6R1/8/p7/2r5/1k6/5K2/8/8 b - - 2 59}

\moves{59...a5? 60.\K e2 \K b3 61.\K d2}
0-1\par
```

**3. The book** - as often as you like; it reads no data:

```
scripts\build_report.bat
```

Runs `pdflatex` twice on `report.tex` (the second run fills in diagram
references) and writes `output\report.pdf`. LaTeX's helper files are removed;
on failure the error is shown and `output\report.log` stays.

Paths are relative to this repository folder.

## Requirements

- Python 3.8 or newer with python-chess (`py -m pip install chess`; already there if
  chessticize-worker runs with the same Python). It replays the games for the positions.
- For the PDF: `pdflatex` with the packages `pgfplots`, `chessboard`, `hyperref`,
  `array`, `geometry`, `xcolor`, `lmodern` (MiKTeX installs missing packages
  on first use; on TeX Live, `chessboard` is in `texlive-games`).

## Tests

```
PYTHONPATH=src python -m pytest tests
```

The tests use a small hand-made sample in `tests/fixtures/`, not the real data.
