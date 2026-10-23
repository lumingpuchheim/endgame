@echo off
rem Compile book.tex to output\book.pdf. Reads no data: run
rem update_statistics.bat first when the data has changed.
rem
rem Usage (from anywhere):
rem   build_book.bat

setlocal
set "REPO=%~dp0.."
cd /d "%REPO%"
call "%~dp0compile_book.cmd"
echo.
pause
