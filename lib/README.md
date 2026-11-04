# The library

Basic knowledge that more than one band may need: a rule, a typical position. Each unit is one file,
`lib/<name>.tex`, and starts with a heading that carries `\label{<name>}`.

A unit is printed only in a book that uses it. A note or a text uses it by referring to it:

    \xref{Section}{bahr-rule}     a reference the reader can follow
    \uses{bahr-rule}              no visible text, only "this needs the unit"

When make_book writes the chapters, in book order, it puts each used unit into the book once, just
before the first position (or your own text) that uses it. A unit can use other units in the same
way; they are printed before it. A unit that no position in the band uses is left out, so every
band's book is complete on its own, and no book refers to another.
