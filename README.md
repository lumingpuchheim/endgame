# Endgame report

Answers two questions from engine-annotated tournament games and writes the
answer as HTML, LaTeX and PDF in one run:

1. **Which endgames are the most common?**
   How many of 100 games reach each endgame type and each material.
2. **Which endgames are tricky?**
   Blunders per 100 games that reached the endgame, with a 95% range and the
   number of games behind every value.

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

It writes exactly three files to `output/`:

| File | What it is |
|---|---|
| `report.html` | Self-contained page; bars are HTML boxes, no image files |
| `report.tex` | LaTeX source; charts are pgfplots commands with the numbers in them |
| `report.pdf` | Compiled from `report.tex` with `pdflatex` |

No intermediate files are kept: LaTeX's helper files are removed after a
successful run (on failure, `report.log` stays so the error can be read).

Options:

| Option | Default | Meaning |
|---|---|---|
| `--input FOLDER` | `input` | Folder with annotated PGN files or links to them |
| `--out FOLDER` | `output` | Where the three files go |
| `--name NAME` | `report` | File name without extension |
| `--min-elo N` | none | Only games where both players are rated N or more |
| `--min-games N` | 100 | Smallest number of games for a value to be ranked |
| `--top N` | 25 | Rows in the material tables |
| `--no-pdf` | | Write HTML and LaTeX only |

Paths are relative to this repository folder.

## Requirements

- Python 3.8 or newer. No Python packages are needed.
- For the PDF: `pdflatex` with the packages `pgfplots`, `booktabs`, `array`,
  `geometry`, `lmodern` (MiKTeX installs missing packages on first use;
  TeX Live has them in `texlive-pictures` and `texlive-latex-extra`).

## Tests

```
PYTHONPATH=src python -m pytest tests
```

The tests use a small hand-made sample in `tests/fixtures/`, not the real data.
