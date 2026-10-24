@echo off
rem The whole book in one command. Brings the chapters up to date, then compiles
rem book.tex to output\book.pdf. It prints what it did with every chapter file.
rem
rem   Statistics (Part I, appendix): rewritten only when the data or the settings
rem   changed. A file you have edited is kept; you get a warning if it is out of date.
rem   Endgame chapters: each written only if it does not exist yet; after that it is yours.
rem   Boards: drawn once and kept in output\boards; only new positions are drawn.
rem
rem Usage (from anywhere):
rem   make_book.bat --min-elo 2600 [--keep-statistics] [--only CHAPTER] [--force] [--show N] [--per-section N] [--input FOLDER] [--min-games N] [--top N]
rem
rem   --only rook-endgames: typeset only that chapter into output\draft.pdf (fast).
rem   --force: compile even if nothing changed.
rem
rem   --keep-statistics: leave the statistics as they are (e.g. while the annotation run is going).

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
%PY% -m endgame_book %*

:end
echo.
pause
