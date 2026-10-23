@echo off
rem Read the data and write Part I and the appendix of the book into chapters\.
rem Run it when the data has changed; build_book.bat does not read the data.
rem
rem Usage (from anywhere):
rem   update_statistics.bat [--min-elo N] [--input FOLDER] [--min-games N] [--top N] [--chapters FOLDER]

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
