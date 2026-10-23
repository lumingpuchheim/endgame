@echo off
rem List the positions where a blunder was made in one material, simplest first.
rem
rem Usage (from anywhere):
rem   list_positions.bat [--min-elo N] [--material "R v R"] [--show N] [--input FOLDER]
rem
rem Paths are relative to the repository folder. Nothing is written.

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
%PY% -m endgame_book.list_positions %*

:end
echo.
pause
