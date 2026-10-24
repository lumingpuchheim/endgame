@echo off
rem Compile the book (python -m endgame_book.compile). Called by list_positions.bat,
rem which sets PY and PYTHONPATH. Sets errorlevel 1 on failure.
%PY% -m endgame_book.compile
exit /b %errorlevel%
