@echo off
rem A book of whole games with your own comments, e.g. chapter 6 of myChessNotebook.
rem
rem Usage (from anywhere):
rem   make_games.bat grandmaster-plays            check every move in games\grandmaster-plays, then build
rem                                               books\grandmaster-plays\Grandmaster-Plays.pdf
rem   make_games.bat grandmaster-plays --check    only check the moves
rem
rem Format of the files: see src\endgame_book\gamebook.py.

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
%PY% -m endgame_book.gamebook %*

:end
echo.
pause
