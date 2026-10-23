# Endgame report

Answers three questions from engine-annotated tournament games and writes the
answer as LaTeX and PDF in one run:

1. **Which endgames are the most common?**
   For each material (e.g. `RB v RN`), how many of 100 games reach it.
2. **Which endgames are tricky?**
   For each material reached in at least 500 games, blunders per 100 games
   that reached it, with the number of games behind every value.
3. **Which endgames cause the most blunders overall?**
   Blunders made in each material per 100 games played: how often it happens
   times how often it goes wrong. These are the endgames worth studying first.
4. **Rook endings, one game:** the game with the rook-vs-rook blunder that has
   the fewest pieces on the board, with every blunder in it, simplest
   position first: a board diagram,
   the move played, the best move, how the game went on, the FEN and a link
   that opens the position on Lichess.

The report reads annotated PGN files made by `chessticize-worker`
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

## Building the report

One command, from this repository folder:

```
scripts\build_report.bat --min-elo 2600
```

or on any system:

```
PYTHONPATH=src python -m endgame_report --min-elo 2600
```

It writes exactly two files to `output/`:

| File | What it is |
|---|---|
| `report.tex` | LaTeX source; bars are pgfplots commands, boards are `chessboard` diagrams from the FEN |
| `report.pdf` | Compiled from `report.tex` with `pdflatex` |

No intermediate files are kept: LaTeX's helper files are removed after a
successful run (on failure, `report.log` stays so the error can be read).

Options:

| Option | Default | Meaning |
|---|---|---|
| `--input FOLDER` | `input` | Folder with annotated PGN files or links to them |
| `--out FOLDER` | `output` | Where the two files go |
| `--name NAME` | `report` | File name without extension |
| `--min-elo N` | none | Only games where both players are rated N or more |
| `--min-games N` | 500 | Smallest number of games for a material to be ranked as tricky |
| `--top N` | 25 | Rows in the material tables |
| `--no-pdf` | | Write the LaTeX file only |

Paths are relative to this repository folder.

## Requirements

- Python 3.8 or newer. No Python packages are needed.
- For the PDF: `pdflatex` with the packages `pgfplots`, `chessboard`, `hyperref`,
  `array`, `geometry`, `xcolor`, `lmodern` (MiKTeX installs missing packages
  on first use; on TeX Live, `chessboard` is in `texlive-games`).

## Tests

```
PYTHONPATH=src python -m pytest tests
```

The tests use a small hand-made sample in `tests/fixtures/`, not the real data.
