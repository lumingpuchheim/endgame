@echo off
rem Compile book.tex to output\book.pdf. Reads no data: run
rem update_statistics.bat first when the data has changed.
rem
rem Usage (from anywhere):
rem   build_book.bat

setlocal
set "REPO=%~dp0.."
cd /d "%REPO%"

where pdflatex >nul 2>nul
if errorlevel 1 (
    echo pdflatex was not found. Install MiKTeX: https://miktex.org/download
    goto end
)
if not exist output mkdir output

rem Twice: the second run fills in the diagram references.
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=output book.tex >nul
if errorlevel 1 goto failed
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=output book.tex >nul
if errorlevel 1 goto failed

del /q output\book.aux output\book.log output\book.out output\book.toc 2>nul
echo Written: output\book.pdf
goto end

:failed
echo pdflatex failed. The error:
findstr /n /c:"!" output\book.log
echo Full log: output\book.log

:end
echo.
pause
