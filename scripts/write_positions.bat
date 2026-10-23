@echo off
rem Write the simplest positions of one material, with the rest of each game, to a
rem LaTeX file you name. Also prints the counts per pawn balance and every position.
rem
rem Usage (from anywhere):
rem   write_positions.bat FILE --min-elo 2600 [--show N] [--per-section N] [--material "R v R"] [--overwrite]
rem
rem Example:
rem   write_positions.bat chapters\rook-draft.tex --min-elo 2600 --show 60 --per-section 20

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
%PY% -m endgame_book.write_positions %*

:end
echo.
pause
