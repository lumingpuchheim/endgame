@echo off
rem List the positions where a blunder was made in one material, simplest first.
rem
rem Usage (from anywhere):
rem   list_positions.bat [--min-elo N] [--max-elo N] [--elo-rule both|average] [--material "R v R"] [--show N] [--input FOLDER]
rem
rem Paths are relative to the repository folder. With --latex FILE the positions
rem are written to FILE and the book is compiled to output\book.pdf.

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
if errorlevel 1 goto end

rem With --latex the chapter has changed: compile the book right away.
echo %* | findstr /c:"--latex" >nul
if not errorlevel 1 call "%~dp0compile_book.cmd" %*

:end
echo.
pause
