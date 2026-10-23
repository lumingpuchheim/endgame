@echo off
rem Compile report.tex to output\report.pdf. Reads no data: run
rem update_statistics.bat first when the data has changed.
rem
rem Usage (from anywhere):
rem   build_report.bat

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
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=output report.tex >nul
if errorlevel 1 goto failed
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=output report.tex >nul
if errorlevel 1 goto failed

del /q output\report.aux output\report.log output\report.out 2>nul
echo Written: output\report.pdf
goto end

:failed
echo pdflatex failed. The error:
findstr /n /c:"!" output\report.log
echo Full log: output\report.log

:end
echo.
pause
