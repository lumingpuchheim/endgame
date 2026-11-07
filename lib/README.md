# The library

Basic knowledge that more than one chapter or band may need: a rule, a typical position, a word.
It is kept apart from the books, like a program library from the programs that use it.

## Units

Each unit is one file, `lib/<name>.tex`, and starts with a heading that carries `\label{<name>}`
(or a diagram labelled `<name>`). Examples: `bahr-rule`, `key-squares`, `side-checks`, `lucena`.

A unit is printed only in a book that uses it. A note or a text uses a unit by referring to it:

    \xref{Section}{bahr-rule}     a reference the reader can follow
    \term{side-checks}            a glossary word of the same name as a unit
    \uses{good-placement}         no visible text, only "this needs the unit"

When make_book writes the chapters, in book order, it puts each used unit into the book once:
just before the first position that uses it, or just after your own text (an introduction) that
uses it. A unit can use other units in the same way; they are printed before it. A unit that no
position or text of the band uses is left out.

## Words

`lib/glossary.tex` defines every word of the glossary once, with the kind of ending it belongs to.
Notes and texts only refer to words, with `\term{key}` or `\termas{key}{other words}`. A book's
glossary lists only the words that book uses.

So every band's book is complete on its own, and no book refers to another.

In the second book of a band, the units are printed together in one chapter at the start, grouped by
the kind of ending they come from. The kind is taken from the unit's first index entry ("Rook!..."
means rook endings); a line `% ending: Bishop endings` in the unit sets it when the index entry does
not say it.
