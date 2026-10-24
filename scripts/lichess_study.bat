@echo off
rem Write random complicated positions of one material as PGN for a Lichess study.
rem
rem Usage (from anywhere):
rem   lichess_study.bat --out FILE [--min-elo N] [--max-elo N] [--elo-rule both|average]
rem                     [--material "R v R"] [--count 32] [--min-pawns 3] [--seed 1] [--no-moves]
rem
rem Example:
rem   lichess_study.bat --out studies\rook-1.pgn --min-elo 1500 --max-elo 1599 --elo-rule average
rem
rem Paths are relative to the repository folder. Another --seed gives other positions.
rem In Lichess: open a study, "Add chapter" -> "PGN", paste the file. Each game becomes a chapter.

setlocal
set "REPO=%~dp0.."
cd /d "%REPO%"

set PY=
where py >nul 2>nul && set PY=py
if not defined PY where python >nul 2>nul && set PY=python
if not defined PY (
    echo Python was not found. Install it from https://www.python.org/downloads/
    goto end
)

set "PYTHONPATH=%REPO%\src"
%PY% -m endgame_book.lichess_study %*

:end
echo.
pause
