@echo off
rem Build the endgame report (HTML, LaTeX, PDF) in one run.
rem
rem Usage (from anywhere):
rem   build_report.bat [--min-elo N] [--input FOLDER] [--out FOLDER] [other options]
rem
rem Paths are relative to the repository folder. See README.md for all options.

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
%PY% -m endgame_report %*

:end
echo.
pause
