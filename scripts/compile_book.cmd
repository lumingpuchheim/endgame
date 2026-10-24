@echo off
rem Compile book.tex to output\book.pdf. Used by make_book.bat and list_positions.bat;
rem run from the repository folder. Sets errorlevel 1 on failure.

where pdflatex >nul 2>nul
if errorlevel 1 (
    echo pdflatex was not found. Install MiKTeX: https://miktex.org/download
    exit /b 1
)
if not exist output mkdir output
echo Compiling the book ...

rem First run, then the glossary (as in peace_mind), then twice more for references.
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=output book.tex >nul
if errorlevel 1 goto failed
if exist output\book.glo (
    pushd output
    makeglossaries book >nul
    if errorlevel 1 echo makeglossaries failed: the glossary is left out. See output\book.glg
    popd
)
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=output book.tex >nul
if errorlevel 1 goto failed
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=output book.tex >nul
if errorlevel 1 goto failed

del /q output\book.aux output\book.log output\book.out output\book.toc output\book.glo output\book.gls output\book.glg output\book.ist 2>nul
echo Written: output\book.pdf
exit /b 0

:failed
echo pdflatex failed. The error:
findstr /n /c:"!" output\book.log
echo Full log: output\book.log
exit /b 1
