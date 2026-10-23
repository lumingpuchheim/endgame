@echo off
rem Everything in one run: reads the data, updates the statistics (Part I and the
rem appendix), writes the rook positions, and compiles the book.
rem
rem Usage (from anywhere):
rem   make_book.bat --min-elo 2600 [--show N] [--per-section N] [--input FOLDER] [--min-games N] [--top N]
rem
rem Writes chapters\where-the-mistakes-are.tex, chapters\how-the-numbers-were-made.tex,
rem chapters\rook-endgames.tex (replaced every run) and output\book.pdf.

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
if errorlevel 1 goto end
call "%~dp0compile_book.cmd"

:end
echo.
pause
