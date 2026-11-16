"""The book as an ebook (EPUB 3), for Kindle Direct Publishing and other ebook shops.

    python -m endgame_book.epub --min-elo 1500 --max-elo 1599 --elo-rule average
    (or scripts\\make_epub.bat with the same options)

It reads the same files as the PDF (book.tex's order: preface, introduction, Part I, the endgame
chapters, epilogue, appendix) and writes books/<band>/Endgames-Elo-<band>.epub (book one) or
...-Two-Pieces.epub (--two-pieces). The PDF must have been built first: the boards come from the
board cache (output/boards), and the cover is page 1 of the PDF.

What changes against the PDF:
- one column of text that the reader's device flows to its screen; no page numbers;
- the boards are pictures of the boards in the PDF; the charts become tables;
- the margin notes "Top idea" stand under the paragraph instead;
- no index (an ebook is searched instead); the glossary and the bibliography stay;
- pieces in moves are letters (Kf3), because not every ebook reader has the chess figures.

Needs PyMuPDF (py -m pip install pymupdf) to turn the boards and the cover into pictures."""

import argparse
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import uuid
import zipfile
from typing import Dict, List, Optional, Tuple

from . import boards as board_cache
from .compile import add_band_options, band_from

PIECES = {"K": "K", "Q": "Q", "R": "R", "B": "B", "N": "N"}
BOARD_WIDTH = 500                       # pixels; grayscale PNG, about 9 KB a board
COVER_HEIGHT = 2560                     # KDP's recommended cover: 1600 x 2560


# ---------------------------------------------------------------------------------------------
# Reading LaTeX
# ---------------------------------------------------------------------------------------------

def strip_comments(text: str) -> str:
    """Remove % comments (not \\%), and the line break after a comment, as TeX does."""
    out = []
    for line in text.split("\n"):
        m = re.search(r"(?<!\\)%", line)
        if m:
            out.append(line[:m.start()] + "\x00")      # \x00: the line ended in a comment
        else:
            out.append(line)
    joined = "\n".join(out)
    return re.sub(r"\x00\n[ \t]*", "", joined).replace("\x00", "")


def read_group(text: str, pos: int) -> Tuple[str, int]:
    """The contents of the {...} group starting at text[pos] (after spaces), and the position after it."""
    while pos < len(text) and text[pos] in " \t\n":
        pos += 1
    if pos >= len(text) or text[pos] != "{":
        # a single token as argument, e.g. \K e5 has no braces: not used that way here
        return "", pos
    depth, start = 0, pos
    while pos < len(text):
        c = text[pos]
        if c == "\\":
            pos += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:pos], pos + 1
        pos += 1
    return text[start + 1:], pos


def read_optional(text: str, pos: int) -> Tuple[Optional[str], int]:
    """An optional [...] argument at text[pos] (no spaces before it), or None."""
    if pos < len(text) and text[pos] == "[":
        end = text.find("]", pos)
        if end > 0:
            return text[pos + 1:end], end + 1
    return None, pos


def environment_body(text: str, pos: int, name: str) -> Tuple[str, int]:
    """The body of \\begin{name} ... \\end{name}, nested ones included; pos is after \\begin{name}."""
    depth, i = 1, pos
    pattern = re.compile(r"\\(begin|end)\{" + re.escape(name) + r"\}")
    while True:
        m = pattern.search(text, i)
        if not m:
            return text[pos:], len(text)
        depth += 1 if m.group(1) == "begin" else -1
        if depth == 0:
            return text[pos:m.start()], m.end()
        i = m.end()


def typography(text: str) -> str:
    """Plain text with TeX's typographical conventions, escaped for XHTML."""
    text = html.escape(text, quote=False)
    text = text.replace("---", "\u2014").replace("--", "\u2013")
    text = text.replace("``", "\u201c").replace("''", "\u201d").replace("`", "\u2018")
    text = text.replace("~", "\u00a0")
    return text


def slug(label: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", label).strip("-") or "x"


def roman(n: int) -> str:
    out = ""
    for value, letters in ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= value:
            out, n = out + letters, n - value
    return out


def parse_bib(path: str) -> Dict[str, Dict[str, str]]:
    entries = {}
    if not os.path.exists(path):
        return entries
    text = open(path, encoding="utf-8").read()
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,(.*?)\n\}", text, re.S):
        fields = {k.lower(): v.strip() for k, v in re.findall(r"(\w+)\s*=\s*\{(.*?)\}\s*,?\s*\n", m.group(3), re.S)}
        fields["type"] = m.group(1).lower()
        entries[m.group(2)] = fields
    return entries


def parse_glossary(path: str) -> Dict[str, Dict[str, str]]:
    """{key: {name, text, description}} from \\newglossaryentry commands."""
    text = strip_comments(open(path, encoding="utf-8").read()) if os.path.exists(path) else ""
    out, pos = {}, 0
    while True:
        i = text.find("\\newglossaryentry", pos)
        if i < 0:
            return out
        key, pos = read_group(text, i + len("\\newglossaryentry"))
        body, pos = read_group(text, pos)
        fields, j = {}, 0
        while True:
            m = re.compile(r"\s*,?\s*(\w+)\s*=\s*").match(body, j)
            if not m or m.end() >= len(body):
                break
            value, j = read_group(body, m.end())
            fields[m.group(1)] = value
        fields.setdefault("text", fields.get("name", key))
        out[key] = fields


# ---------------------------------------------------------------------------------------------
# The book as a list of files, as book.tex puts it together
# ---------------------------------------------------------------------------------------------

def book_parts(band, book: str = "one") -> List[Tuple[str, str]]:
    """[(kind, value), ...]: 'file' (a .tex file to read), 'part' (title|label), 'mainmatter', 'appendix'."""
    ch = band.chapters
    two = book == "two"
    parts = [("frontfile", "preface.tex"), ("frontfile", "introduction.tex"), ("mainmatter", ""),
             ("part", "Where the Mistakes Are|part:mistakes"),
             ("file", os.path.join(ch, "where-the-mistakes-are-two-pieces.tex" if two else "where-the-mistakes-are.tex")),
             ("part", "The Endgames|part:endgames"),
             ("topideas", os.path.join(ch, "top-ideas-two-pieces.tex" if two else "top-ideas.tex"))]
    if two:
        parts.append(("file", os.path.join(ch, "basics-two-pieces.tex")))
    parts += [("file", os.path.join(ch, "endgames.tex")),
              ("file", os.path.join(ch, "epilogue-two-pieces.tex" if two else "epilogue.tex")),
              ("appendix", ""),
              ("file", os.path.join(ch, "how-the-numbers-were-made-two-pieces.tex" if two
                                    else "how-the-numbers-were-made.tex"))]
    return parts


def title_of(band, book: str) -> Tuple[str, str]:
    """(title, subtitle) as the PDF's cover has them, from books/<band>/texts/title*.tex."""
    title, subtitle = "Where Players Go Wrong in the Endgame", ""
    name = "title-two-pieces.tex" if book == "two" else "title.tex"
    path = os.path.join(band.folder, "texts", name)
    if os.path.exists(path):
        text = strip_comments(open(path, encoding="utf-8").read())
        for command in ("egpdftitle", "egsubtitle"):
            m = re.search(r"\\(?:re)?newcommand\{\\" + command + r"\}", text)
            if m:
                value, _ = read_group(text, m.end())
                value = re.sub(r"\\\\(\[[^\]]*\])?", " ", value).strip()
                if command == "egpdftitle":
                    title = value
                else:
                    subtitle = value
    return title, subtitle


# ---------------------------------------------------------------------------------------------
# The converter
# ---------------------------------------------------------------------------------------------

class Chapter:
    """One XHTML file of the ebook."""
    def __init__(self, ident: str, title: str, level: int, kind: str):
        self.ident, self.title, self.level, self.kind = ident, title, level, kind
        self.blocks: List[str] = []
        self.sections: List[Tuple[str, str]] = []      # (anchor, title) for the contents


class Converter:
    """LaTeX of this book to XHTML chapters. Run twice: the first run finds the numbers of all labels
    (diagrams, chapters, sections), the second writes the text with the links."""

    def __init__(self, band, book: str = "one", root: str = "."):
        self.band, self.book, self.root = band, book, root
        self.glossary = parse_glossary(os.path.join(root, "lib", "glossary.tex"))
        self.bib = parse_bib(os.path.join(root, "refs.bib"))
        self.labels: Dict[str, Tuple[str, str]] = {}       # label: (number as printed, href)
        self.boards: Dict[str, str] = {}                   # image name: FEN or keysquares spec
        self.cited: List[str] = []
        self.terms_used: List[str] = []

    # --- state for one run ---
    def reset(self):
        self.chapters: List[Chapter] = []
        self.chapter: Optional[Chapter] = None
        self.tokens: List[Tuple[str, str]] = []
        self.counters = {"part": 0, "chapter": 0, "section": 0, "diagram": 0, "exercise": 0}
        self.current_label = ""
        self.matter = "front"
        self.game: Optional[Tuple[str, str, str]] = None
        self.top_ideas: Dict[str, str] = {}
        self.starred: set = set()
        self.in_unit = 0
        self.headings = 0

    # --- output ---
    def emit(self, kind: str, value: str = ""):
        self.tokens.append((kind, value))

    def flush(self):
        """Turn the tokens of the current chapter into blocks: running text becomes paragraphs."""
        if self.chapter is None:
            self.tokens = []
            return
        para: List[str] = []
        pending_top: List[str] = []

        def close():
            text = "".join(para).strip()
            if text:
                cls = ""
                if text.startswith("\x01right\x01"):
                    text, cls = text[len("\x01right\x01"):], ' class="right"'
                self.chapter.blocks.append(f"<p{cls}>{text}</p>")
            para.clear()
            for name in pending_top:
                self.chapter.blocks.append(f'<p class="topidea"><b>Top idea</b> \u00b7 {name}</p>')
            pending_top.clear()

        for kind, value in self.tokens:
            if kind == "text":
                para.append(value)
            elif kind == "par":
                close()
            elif kind == "top":
                pending_top.append(value)
            else:                                   # block
                close()
                self.chapter.blocks.append(value)
        close()
        self.tokens = []

    def new_chapter(self, title: str, level: int, kind: str, anchor_label: str = "") -> Chapter:
        self.flush()
        ident = f"c{len(self.chapters) + 1:03d}"
        self.chapter = Chapter(ident, title, level, kind)
        self.headings = 0
        self.chapters.append(self.chapter)
        return self.chapter

    def href(self, anchor: str) -> str:
        return f"{self.chapter.ident}.xhtml#{anchor}" if self.chapter else f"#{anchor}"

    def label(self, name: str):
        anchor = slug(name)
        if name not in self.labels or self.labels[name][1] != self.href(anchor):
            self.labels[name] = (self.current_label, self.href(anchor))
        self.emit("text", f'<span id="{anchor}"></span>')

    # --- reading ---
    def include(self, path: str):
        full = os.path.join(self.root, path)
        if not path.endswith(".tex"):
            full += ".tex"
        if os.path.exists(full):
            self.convert(strip_comments(open(full, encoding="utf-8").read()))

    def run(self) -> List[Chapter]:
        self.reset()
        for kind, value in book_parts(self.band, self.book):
            if kind == "frontfile":
                self.include(value)
            elif kind == "mainmatter":
                self.matter = "main"
            elif kind == "appendix":
                self.matter = "appendix"
                self.counters["chapter"] = 0
            elif kind == "part":
                title, name = value.split("|")
                self.counters["part"] += 1
                self.current_label = roman(self.counters["part"])
                self.new_chapter(f"Part {roman(self.counters['part'])}: {title}", 0, "part")
                self.emit("block", f'<h1 class="part"><span class="partnum">Part {roman(self.counters["part"])}'
                                   f'</span><br/>{typography(title)}</h1>')
                self.label(name)
            elif kind == "topideas":
                self.include(value)
            else:
                self.include(value)
        self.flush()
        return self.chapters

    def convert(self, text: str):
        """Read LaTeX and emit tokens."""
        pos, buf = 0, []

        def text_out():
            if buf:
                chunk = "".join(buf)
                buf.clear()
                parts = re.split(r"\n[ \t]*\n\s*", chunk)
                for i, part in enumerate(parts):
                    if i:
                        self.emit("par")
                    part = re.sub(r"\s+", " ", part)
                    if part:
                        self.emit("text", typography(part))

        while pos < len(text):
            c = text[pos]
            if c == "\\":
                m = re.compile(r"\\([A-Za-z@]+\*?|.)").match(text, pos)
                name = m.group(1)
                text_out()
                pos = self.command(name, text, m.end())
            elif c in "{}":
                text_out()
                pos += 1
            elif c == "$":
                end = text.find("$", pos + 1)
                buf.append(text[pos + 1:end if end > 0 else len(text)])
                pos = end + 1 if end > 0 else len(text)
            else:
                buf.append(c)
                pos += 1
        text_out()

    def inline(self, latex: str) -> str:
        """Convert a piece of LaTeX that stays within one paragraph; returns XHTML."""
        saved, self.tokens = self.tokens, []
        self.convert(latex)
        out = "".join(v for k, v in self.tokens if k == "text")
        tops = [v for k, v in self.tokens if k == "top"]
        self.tokens = saved
        for t in tops:
            self.emit("top", t)
        return re.sub(r"\s+", " ", out).strip()

    # --- commands ---
    def command(self, name: str, text: str, pos: int) -> int:
        star = name.endswith("*")
        base = name.rstrip("*")
        arg = lambda p: read_group(text, p)

        if base in PIECES:                              # \K e5 -> Ke5
            m = re.compile(r"(\{\})?[ \t]*").match(text, pos)
            self.emit("text", PIECES[base])
            return m.end()
        if name in ("%", "&", "#", "_", "$"):
            self.emit("text", typography(name))
            return pos
        if name == "\\":                                # line break, maybe \\[4pt]
            _o, pos = read_optional(text, pos)
            self.emit("text", "<br/>")
            return pos
        if name in (",", " ", ";"):
            self.emit("text", " " if name != "," else "\u202f")
            return pos
        if name == "par":
            self.emit("par")
            return pos

        if base == "part":
            title, pos = arg(pos)
            return pos
        if base == "chapter":
            title, pos = arg(pos)
            plain = re.sub(r"<[^>]+>", "", self.inline(title))
            if not star and self.matter != "front":
                self.counters["chapter"] += 1
                self.counters["section"] = 0
                number = (chr(64 + self.counters["chapter"]) if self.matter == "appendix"
                          else str(self.counters["chapter"]))
                self.current_label = number
                word = "Appendix" if self.matter == "appendix" else "Chapter"
                shown = f"Appendix {number}" if self.matter == "appendix" else number
                self.new_chapter(f"{shown}. {plain}", 1, "chapter")
                self.emit("block", f'<h1><span class="chapnum">{word} {number}</span><br/>{self.inline(title)}</h1>')
            else:
                self.new_chapter(plain, 1, "chapter")
                self.emit("block", f"<h1>{self.inline(title)}</h1>")
            return pos
        if base in ("section", "subsection", "paragraph"):
            title, pos = arg(pos)
            level = {"section": 2, "subsection": 3, "paragraph": 4}[base]
            number = ""
            if base == "section" and not star and self.matter != "front":
                self.counters["section"] += 1
                chap = (chr(64 + self.counters["chapter"]) if self.matter == "appendix"
                        else str(self.counters["chapter"]))
                number = f"{chap}.{self.counters['section']}"
                self.current_label = number
            self.headings += 1
            anchor = f"h{self.headings}"
            heading = self.inline(title)
            if self.chapter is not None and level <= 2:
                self.chapter.sections.append((anchor, (number + " " if number else "") + re.sub(r"<[^>]+>", "", heading)))
            self.emit("block", f'<h{level} id="{anchor}">{number + " " if number else ""}{heading}</h{level}>')
            return pos
        if base == "label":
            value, pos = arg(pos)
            self.label(value)
            return pos
        if base in ("index",):
            value, pos = arg(pos)
            if not self.in_unit and value in self.top_ideas and self.chapter is not None:
                key = (self.chapter.ident, value)
                if key not in self.starred:
                    self.starred.add(key)
                    self.emit("top", typography(self.top_ideas[value]))
            return pos
        if base in ("indexonly", "uses", "addcontentsline", "phantomsection", "vspace", "hspace",
                    "needspace", "thispagestyle", "pagestyle", "clearpage", "newpage", "nopagebreak",
                    "bigskip", "medskip", "smallskip", "noindent", "raggedright", "centering",
                    "footnotesize", "small", "scriptsize", "large", "Large", "normalsize", "arraybackslash",
                    "hfill", "vfill", "enspace", "quad", "qquad", "relax", "protect"):
            n = {"addcontentsline": 3, "indexonly": 1, "uses": 1, "vspace": 1, "hspace": 1, "needspace": 1,
                 "thispagestyle": 1, "pagestyle": 1}.get(base, 0)
            for _ in range(n):
                _v, pos = arg(pos)
            if base in ("enspace", "quad", "qquad", "hfill"):
                self.emit("text", " ")
            return pos
        if base in ("textbf", "moves"):
            value, pos = arg(pos)
            self.emit("text", f"<b>{self.inline(value)}</b>")
            return pos
        if base in ("emph", "textit"):
            value, pos = arg(pos)
            self.emit("text", f"<i>{self.inline(value)}</i>")
            return pos
        if base == "texttt":
            value, pos = arg(pos)
            self.emit("text", f"<code>{self.inline(value)}</code>")
            return pos
        if base == "textsc":
            value, pos = arg(pos)
            self.emit("text", f'<span class="sc">{self.inline(value)}</span>')
            return pos
        if base == "textcolor":
            color, pos = arg(pos)
            value, pos = arg(pos)
            cls = ' class="muted"' if color == "muted" else ""
            self.emit("text", f"<span{cls}>{self.inline(value)}</span>")
            return pos
        if base == "textbackslash":
            self.emit("text", "\\")
            return pos
        if base == "copyright":
            self.emit("text", "\u00a9")
            return pos
        if base == "textperiodcentered":
            self.emit("text", "\u00b7")
            return pos
        if base in ("ldots", "dots"):
            self.emit("text", "\u2026")
            return pos

        if base == "term":
            key, pos = arg(pos)
            self.emit("text", self.term(key, None))
            return pos
        if base == "termas":
            key, pos = arg(pos)
            words, pos = arg(pos)
            self.emit("text", self.term(key, words))
            return pos
        if base == "vocab":
            _o, pos = read_optional(text, pos)
            key, pos = arg(pos)
            words, pos = arg(pos)
            _meaning, pos = arg(pos)
            self.emit("text", self.term(key, words))
            return pos
        if base == "xref":
            word, pos = arg(pos)
            target, pos = arg(pos)
            self.emit("text", self.xref(word, target))
            return pos
        if base == "ref":
            target, pos = arg(pos)
            number, link = self.labels.get(target, ("", ""))
            self.emit("text", f'<a href="{link}">{number}</a>' if link else number)
            return pos
        if base == "cite":
            _o, pos = read_optional(text, pos)
            keys, pos = arg(pos)
            refs = []
            for key in [k.strip() for k in keys.split(",")]:
                if key not in self.cited:
                    self.cited.append(key)
                refs.append(f'<a href="bib.xhtml#bib-{slug(key)}">{self.cite_number(key)}</a>')
            self.emit("text", "[" + ", ".join(refs) + "]")
            return pos

        if base == "game":
            white, pos = arg(pos)
            black, pos = arg(pos)
            event, pos = arg(pos)
            self.game = (self.inline(white), self.inline(black), self.inline(event))
            return pos
        if base == "samegame":
            self.game = None
            return pos
        if base == "diagram":
            label, pos = read_optional(text, pos)
            fen, pos = arg(pos)
            self.diagram(fen.strip(), label)
            return pos
        if base == "seen":
            target, pos = arg(pos)
            self.emit("par")
            self.emit("text", f"We have already seen this position in {self.xref('diagram', target)}.")
            self.emit("par")
            return pos
        if base == "skipped":
            n, pos = arg(pos)
            self.emit("par")
            self.emit("text", f"After {typography(n)} more moves:")
            self.emit("par")
            return pos
        if base == "keysquares":
            fen, pos = arg(pos)
            squares, pos = arg(pos)
            caption, pos = arg(pos)
            image = self.board_image(fen.strip(), squares.strip())
            self.emit("block", f'<div class="board"><img src="images/{image}" alt="{html.escape(self.inline(caption))}"/>'
                               f'<p class="caption">{self.inline(caption)}</p></div>')
            return pos
        if base == "exercise":
            fen, pos = arg(pos)
            self.counters["exercise"] += 1
            self.current_label = str(self.counters["exercise"])
            n = self.counters["exercise"]
            image = self.board_image(fen.strip())
            self.emit("block", f'<div class="diagram" id="ex{n}"><p class="dnum">Exercise {n}</p>'
                               f'{self.links(fen.strip())}<img src="images/{image}" alt="{self.alt(fen)}"/></div>')
            return pos

        if base == "yourtext":
            name_, pos = arg(pos)
            band_text = os.path.join(self.band.folder, "texts", name_ + ".tex")
            if os.path.exists(os.path.join(self.root, band_text)):
                self.include(band_text)
            else:
                self.include(os.path.join("texts", name_ + ".tex"))
            return pos
        if base == "libunit":
            name_, pos = arg(pos)
            self.label("lib:" + name_)
            self.in_unit += 1
            self.include(os.path.join("lib", name_ + ".tex"))
            self.in_unit -= 1
            return pos
        if base in ("input", "include", "InputIfFileExists"):
            path, pos = arg(pos)
            if base == "InputIfFileExists":
                _a, pos = arg(pos)
                _b, pos = arg(pos)
            self.include(path)
            return pos
        if base == "chapterfile":
            path, pos = arg(pos)
            _msg, pos = arg(pos)
            self.include(path)
            return pos
        if base == "egbook":
            which, pos = arg(pos)
            body, pos = arg(pos)
            if which == self.book:
                self.convert(body)
            return pos
        if base == "egtopidea":
            entry, pos = arg(pos)
            shown, pos = arg(pos)
            self.top_ideas[entry] = shown
            return pos
        if base in ("newcommand", "renewcommand", "providecommand"):
            _n, pos = arg(pos)
            _o, pos = read_optional(text, pos)
            _b, pos = arg(pos)
            return pos

        if base == "begin":
            env, pos = arg(pos)
            body, pos = environment_body(text, pos, env)
            self.environment(env, body)
            return pos
        if base == "end":
            _env, pos = arg(pos)
            return pos
        if base == "item":
            _o, pos = read_optional(text, pos)
            return pos

        # unknown command: its arguments are read as text
        return pos

    def environment(self, env: str, body: str):
        start = len(self.tokens)
        self._environment(env, body)
        if env in ("itemize", "enumerate", "keypoints"):
            # a "Top idea" note found inside a list goes after the list, not before it
            tops = [t for t in self.tokens[start:] if t[0] == "top"]
            self.tokens[start:] = [t for t in self.tokens[start:] if t[0] != "top"] + tops

    def _environment(self, env: str, body: str):
        if env in ("itemize", "enumerate"):
            items = [i for i in re.split(r"\\item\b", body)[1:]]
            tag = "ul" if env == "itemize" else "ol"
            self.emit("block", f"<{tag}>" + "".join(f"<li>{self.paragraphs(i)}</li>" for i in items) + f"</{tag}>")
        elif env == "keypoints":
            items = [i for i in re.split(r"\\item\b", body)[1:]]
            self.emit("block", '<div class="keypoints"><p class="kphead">What this means for you</p><ul>'
                      + "".join(f"<li>{self.paragraphs(i)}</li>" for i in items) + "</ul></div>")
        elif env == "exercises":
            self.emit("block", '<h3 class="exercises">Exercises</h3>')
            self.emit("text", "Write down your plan and your move first, then check them on Lichess.")
            self.emit("par")
            self.convert(body)
            self.emit("par")
        elif env == "flushright":
            self.emit("par")
            self.emit("text", "\x01right\x01" + self.inline(body))
            self.emit("par")
        elif env == "tabular":
            self.emit("block", self.table(body))
        elif env == "tikzpicture":
            chart = self.chart(body)
            if chart:
                self.emit("block", chart)
        else:                                           # center, basics and the like: just the contents
            self.convert(body)

    def paragraphs(self, latex: str) -> str:
        parts = [p for p in re.split(r"\n[ \t]*\n", latex) if p.strip()]
        if len(parts) <= 1:
            return self.inline(latex)
        return "".join(f"<p>{self.inline(p)}</p>" for p in parts)

    def table(self, body: str) -> str:
        body = re.sub(r"^\s*\{[^\n]*?\}\s*", "", body.strip(), count=1)     # the column specification
        rows = [r for r in re.split(r"\\\\(?:\[[^\]]*\])?", body) if r.strip()]
        out = []
        for row in rows:
            cells = re.split(r"(?<!\\)&", row)
            out.append("<tr>" + "".join(f"<td>{self.inline(c)}</td>" for c in cells) + "</tr>")
        return '<table class="data">' + "".join(out) + "</table>"

    def chart(self, body: str) -> str:
        """A pgfplots bar chart as a table: one row per bar, from the top of the chart down."""
        labels_m = re.search(r"yticklabels=\{(.*?)\}\s*,\s*(?:ymin|enlarge|bar|xmajor|xmin)", body, re.S)
        if not labels_m:
            labels_m = re.search(r"yticklabels=\{((?:\{[^{}]*\},?)+)\}", body)
        if not labels_m:
            return ""
        labels = re.findall(r"\{([^{}]*)\}", labels_m.group(1))
        series = [dict((int(float(y)), float(x)) for x, y in re.findall(r"\(([-\d.]+),([-\d.]+)\)", c))
                  for c in re.findall(r"\\addplot\[[^\]]*\]\s*coordinates\s*\{([^}]*)\}", body)]
        legend_m = re.search(r"\\legend\{([^}]*)\}", body)
        legend = [s.strip() for s in legend_m.group(1).split(",")] if legend_m else []
        notes = re.findall(r"\\node\[[^\]]*\] at \(axis description cs:[\d.]+,([\d.]+)\) \{([^}]*)\};", body)
        stacked = "xbar stacked" in body
        rows = []
        for y in range(len(labels) - 1, -1, -1):
            cells = [typography(labels[y])]
            if notes and not stacked:
                note = next((t for f, t in notes if abs(float(f) - (y + 0.5) / len(labels)) < 0.01), "")
                cells.append(typography(note))
            elif stacked:
                values = [s.get(y, 0.0) for s in series]
                cells += [f"{v:.1f}%" if v else "\u2013" for v in values]
            else:
                cells.append(f"{series[0].get(y, 0.0):g}" if series else "")
            rows.append(cells)
        head = ""
        if stacked and legend:
            head = "<tr><th></th>" + "".join(f"<th>{typography(l)}</th>" for l in legend) + "</tr>"
        return ('<table class="chart">' + head
                + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>")

    def term(self, key: str, words: Optional[str]) -> str:
        entry = self.glossary.get(key)
        shown = self.inline(words) if words is not None else (
            typography(entry["text"]) if entry else typography(key.replace("-", " ")))
        if not entry:
            return shown
        if key not in self.terms_used:
            self.terms_used.append(key)
        return f'<a class="term" href="glossary.xhtml#g-{slug(key)}">{shown}</a>'

    def xref(self, word: str, target: str) -> str:
        number, link = self.labels.get(target, ("", ""))
        text = f"{typography(word)}\u00a0{number}" if number else typography(word)
        return f'<a href="{link}">{text}</a>' if link else text

    def cite_number(self, key: str) -> str:
        order = sorted(self.cited, key=lambda k: (self.bib.get(k, {}).get("author", k).split()[-1],
                                                 self.bib.get(k, {}).get("year", ""),
                                                 self.bib.get(k, {}).get("title", "")))
        return str(order.index(key) + 1) if key in order else "?"

    def alt(self, fen: str) -> str:
        side = "White" if " w" in fen else "Black"
        return f"Chess board. {side} to move. Position {html.escape(fen.split()[0])}"

    def links(self, fen: str) -> str:
        parts = fen.split()
        while len(parts) < 6:
            parts.append({2: "-", 3: "-", 4: "0", 5: "1"}.get(len(parts), "w"))
        side = "white" if parts[1] == "w" else "black"
        play = "https://lichess.org/?fen=" + "%20".join(parts) + f"&amp;color={side}#ai"
        analyse = "https://lichess.org/analysis/standard/" + "_".join(parts)
        return (f'<p class="links"><a href="{play}">Practise against the computer</a> \u00b7 '
                f'<a href="{analyse}">Analyse</a></p>')

    def diagram(self, fen: str, label: Optional[str]):
        self.counters["diagram"] += 1
        n = self.counters["diagram"]
        self.current_label = str(n)
        anchor = slug(label) if label else f"d{n}"
        if label:
            self.labels.setdefault(label, (str(n), self.href(anchor)))
            self.labels[label] = (str(n), self.href(anchor))
        game = ""
        if self.game:
            white, black, event = self.game
            game = f'<p class="game"><b>{white} \u2013 {black}</b><br/><span class="muted">{event}</span></p>'
            self.game = None
        image = self.board_image(fen)
        self.emit("block", f'<div class="diagram" id="{anchor}"><p class="dnum">Diagram {n}</p>'
                           f'{self.links(fen)}{game}<img src="images/{image}" alt="{self.alt(fen)}"/></div>')

    def board_image(self, fen: str, squares: Optional[str] = None) -> str:
        """The picture of a board; with squares (even none), a \\keysquares board, drawn on its own."""
        key = fen if squares is None else fen + "|" + squares
        name = "b" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12] + ".png"
        self.boards[name] = key
        return name


# ---------------------------------------------------------------------------------------------
# Pictures: boards from the board cache, boards with marked squares, the cover
# ---------------------------------------------------------------------------------------------

def _keysquares_tex(specs: List[Tuple[str, str]]) -> str:
    pages = "\n".join(
        "\\begin{egpage}\\chessboard[setfen=%s,showmover=false,boardfontsize=18pt,labelfontsize=7pt,"
        "pgfstyle=color,color=ocre,opacity=0.5,colorbackfields={%s}]\\end{egpage}" % (fen, squares)
        for fen, squares in specs)
    return ("\\documentclass[border=3pt]{standalone}\n\\usepackage{xcolor}\n\\usepackage{chessboard}\n"
            "\\definecolor{ocre}{RGB}{243,102,25}\n"
            "\\newenvironment{egpage}{}{}\n\\standaloneenv{egpage}\n"
            f"\\begin{{document}}\n{pages}\n\\end{{document}}\n")


def draw_boards(wanted: Dict[str, str], folder: str, band, cache: str = board_cache.CACHE) -> List[str]:
    """Write each board as a grayscale PNG (marked squares in colour). Returns the boards it could not draw."""
    import pymupdf
    os.makedirs(folder, exist_ok=True)
    index_path = os.path.join(cache, "index.json")
    index = json.load(open(index_path, encoding="utf-8")) if os.path.exists(index_path) else {}
    plain = {name: key for name, key in wanted.items() if "|" not in key}
    marked = {name: key for name, key in wanted.items() if "|" in key}
    missing = [key for key in plain.values() if key not in index]
    if missing:                                        # draw them into the cache first, as the PDF does
        _draw_into_cache(missing, cache, band)
        index = json.load(open(index_path, encoding="utf-8"))
    failed, docs = [], {}

    def render(pdf: str, page: int, target: str, colour: bool):
        doc = docs.get(pdf) or docs.setdefault(pdf, pymupdf.open(pdf))
        p = doc[page - 1]
        zoom = BOARD_WIDTH / p.rect.width
        pix = p.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom),
                           colorspace=pymupdf.csRGB if colour else pymupdf.csGRAY)
        pix.save(target)

    for name, fen in plain.items():
        target = os.path.join(folder, name)
        if os.path.exists(target):
            continue
        if fen not in index:
            failed.append(fen)
            continue
        pdf, page = index[fen]
        render(os.path.join(cache, pdf), page, target, False)
    if marked:
        specs = sorted(set(tuple(k.split("|", 1)) for k in marked.values()))
        pdf = os.path.join(cache, "keysquares-" + hashlib.sha1(repr(specs).encode()).hexdigest()[:10] + ".pdf")
        if not os.path.exists(pdf):
            base = pdf[:-4]
            with open(base + ".tex", "w", encoding="utf-8") as handle:
                handle.write(_keysquares_tex(specs))
            subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
                            os.path.basename(base) + ".tex"], cwd=cache, capture_output=True)
            for ext in (".aux", ".log", ".tex"):
                if os.path.exists(base + ext):
                    os.remove(base + ext)
        if os.path.exists(pdf):
            for name, key in marked.items():
                render(pdf, specs.index(tuple(key.split("|", 1))) + 1, os.path.join(folder, name), True)
        else:
            failed += [k for k in marked.values()]
    return failed


def _draw_into_cache(fens: List[str], cache: str, band):
    """Boards that are not in the cache yet: one more pdflatex run of the board cache. Afterwards the
    cache's map (boards.tex) is written again for the band's own files, as the PDF build leaves it."""
    from .compile import source_folders
    own = board_cache.tex_files(source_folders(band))
    path = os.path.join(cache, "epub-extra.tex")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("".join(f"\\diagram{{{fen}}}\n" for fen in fens))
    try:
        board_cache.update(cache, files=own + [path])
    finally:
        os.remove(path)
        board_cache.update(cache, files=own)


def draw_cover(pdf: str, target: str) -> bool:
    """Page 1 of the book's PDF (the cover) as a JPEG, 2560 pixels high."""
    import pymupdf
    if not os.path.exists(pdf):
        return False
    page = pymupdf.open(pdf)[0]
    zoom = COVER_HEIGHT / page.rect.height
    page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).save(target, jpg_quality=90)
    return True


# ---------------------------------------------------------------------------------------------
# Writing the EPUB
# ---------------------------------------------------------------------------------------------

CSS = """
body { font-family: serif; line-height: 1.4; margin: 0 2%; }
h1 { font-size: 1.6em; color: #c4501a; margin: 1.5em 0 1em; line-height: 1.2; }
h1.part { text-align: center; margin-top: 30%; font-size: 2em; }
.partnum, .chapnum { font-size: 0.55em; color: #666666; font-variant: small-caps; font-weight: normal; }
h2 { font-size: 1.25em; color: #c4501a; margin: 1.4em 0 0.6em; }
h3 { font-size: 1.1em; margin: 1.2em 0 0.5em; }
h4 { font-size: 1em; margin: 1em 0 0.3em; }
p { margin: 0 0 0.6em; text-align: left; }
p.right { text-align: right; }
.muted { color: #666666; }
.sc { font-variant: small-caps; }
a { color: #c4501a; text-decoration: none; }
a.term { color: inherit; border-bottom: 1px dotted #c4501a; }
div.diagram, div.board { text-align: center; margin: 1.2em 0 0.8em; page-break-inside: avoid; }
div.diagram img, div.board img { width: 80%; max-width: 500px; }
p.dnum { font-weight: bold; color: #c4501a; margin: 0 0 0.2em; text-align: center; }
p.links { font-size: 0.85em; margin: 0 0 0.3em; text-align: center; }
p.game { margin: 0 0 0.4em; text-align: center; }
p.caption { font-size: 0.9em; color: #666666; text-align: center; }
p.topidea { font-size: 0.85em; color: #c4501a; margin: -0.3em 0 0.8em; }
div.keypoints { margin: 1em 0; padding: 0.5em 0.8em; border-left: 3px solid #c4501a; }
p.kphead { font-weight: bold; color: #c4501a; margin: 0 0 0.3em; }
table { border-collapse: collapse; margin: 0.8em 0 1em; width: 100%; }
td, th { padding: 0.2em 0.5em; vertical-align: top; text-align: left; border-bottom: 1px solid #dddddd; }
table.chart td + td, table.chart th + th { text-align: right; white-space: nowrap; }
.title { text-align: center; margin-top: 25%; }
.title h1 { font-size: 2.2em; }
nav ol { list-style-type: none; padding-left: 1em; }
dl dt { font-weight: bold; margin-top: 0.6em; }
dl dd { margin: 0 0 0.4em 1em; }
"""


def xhtml(title: str, body: str) -> str:
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
            'lang="en" xml:lang="en">\n'
            f'<head><meta charset="utf-8"/><title>{html.escape(title)}</title>'
            '<link rel="stylesheet" type="text/css" href="style.css"/></head>\n'
            f'<body>\n{body}\n</body></html>\n')


def bibliography(conv: Converter) -> str:
    order = sorted(conv.cited, key=lambda k: (conv.bib.get(k, {}).get("author", k).split()[-1],
                                             conv.bib.get(k, {}).get("year", ""), conv.bib.get(k, {}).get("title", "")))
    items = []
    for i, key in enumerate(order, 1):
        e = conv.bib.get(key, {})
        parts = [typography(e.get("author", key)), f"<i>{typography(e.get('title', ''))}</i>"]
        if e.get("translator"):
            parts.append("translated by " + typography(e["translator"]))
        parts += [typography(e[f]) for f in ("publisher", "year") if e.get(f)]
        items.append(f'<p id="bib-{slug(key)}">[{i}] ' + ", ".join(p for p in parts if p) + ".</p>")
    return "<h1>Bibliography</h1>\n" + "\n".join(items)


def glossary(conv: Converter) -> str:
    keys = sorted(conv.terms_used, key=lambda k: conv.glossary[k]["name"].lower())
    entries = []
    for key in keys:
        e = conv.glossary[key]
        entries.append(f'<dt id="g-{slug(key)}">{conv.inline(e["name"])}</dt><dd>{conv.inline(e["description"])}</dd>')
    return "<h1>Glossary</h1>\n<dl>" + "".join(entries) + "</dl>"


def write_epub(band, book: str = "one", root: str = ".", out: Optional[str] = None) -> str:
    conv = Converter(band, book, root)
    conv.run()                       # first run: the numbers of all labels
    chapters = conv.run()            # second run: the text, with the links
    job = band.job_two if book == "two" else band.job
    out = out or os.path.join(band.folder, job + ".epub")
    work = os.path.join("output", "epub", job)
    images = os.path.join(work, "images")
    failed = draw_boards(conv.boards, images, band)
    cover = os.path.join(work, "cover.jpg")
    has_cover = draw_cover(os.path.join(band.folder, job + ".pdf"), cover)
    title, subtitle = title_of(band, book)
    ident = "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, "endgame-book/" + job))

    files: List[Tuple[str, str, str]] = []           # (href, media type, content or path:...)
    title_page = ('<div class="title"><h1>' + typography(title) + "</h1>"
                  + (f"<p>{typography(subtitle)}</p>" if subtitle else "")
                  + f'<p class="muted">{typography(band.describe())}</p><p>Ming Lu</p></div>')
    files.append(("title.xhtml", "application/xhtml+xml", xhtml(title, title_page)))
    files.append(("copyright.xhtml", "application/xhtml+xml", xhtml("Copyright", (
        f"<p>{typography(title)}</p><p>{typography(band.describe())}</p>"
        "<p>Copyright \u00a9 2026 Ming Lu. All rights reserved.</p>"
        "<p>Games: The Week in Chess. Analysis: Stockfish.</p>"))))
    drawn = set(os.listdir(images)) if os.path.isdir(images) else set()

    def drop_missing(body: str) -> str:
        """A board that could not be drawn would make the EPUB invalid: say so in the text instead."""
        return re.sub(r'<img src="images/([^"]+)" alt="[^"]*"/>',
                      lambda m: m.group(0) if m.group(1) in drawn else '<p class="caption">(board missing)</p>', body)

    for ch in chapters:
        files.append((ch.ident + ".xhtml", "application/xhtml+xml",
                      xhtml(ch.title, drop_missing("\n".join(ch.blocks)))))
    files.append(("bib.xhtml", "application/xhtml+xml", xhtml("Bibliography", bibliography(conv))))
    files.append(("glossary.xhtml", "application/xhtml+xml", xhtml("Glossary", glossary(conv))))

    # contents: parts hold their chapters
    open_part = None

    def li(href, text):
        return f'<li><a href="{href}">{html.escape(text)}</a>'

    toc = []
    for ch in chapters:
        if ch.kind == "part":
            if open_part is not None:
                toc.append("</ol></li>")
            toc.append(li(ch.ident + ".xhtml", ch.title) + "<ol>")
            open_part = ch
        else:
            subs = "".join(f'<li><a href="{ch.ident}.xhtml#{a}">{html.escape(t)}</a></li>' for a, t in ch.sections)
            toc.append(li(ch.ident + ".xhtml", ch.title) + (f"<ol>{subs}</ol>" if subs else "") + "</li>")
    if open_part is not None:
        toc.append("</ol></li>")
    # the epilogue and the appendix stand outside Part II in the PDF's contents too, but nesting them
    # under the last part is harmless; keep the order simple
    toc.append(li("bib.xhtml", "Bibliography") + "</li>")
    toc.append(li("glossary.xhtml", "Glossary") + "</li>")
    nav = ('<nav epub:type="toc" id="toc"><h1>Contents</h1><ol>' + "".join(toc) + "</ol></nav>"
           '<nav epub:type="landmarks" hidden=""><ol>'
           f'<li><a epub:type="bodymatter" href="{chapters[0].ident}.xhtml">Start</a></li>'
           '<li><a epub:type="toc" href="nav.xhtml">Contents</a></li></ol></nav>')
    files.insert(2, ("nav.xhtml", "application/xhtml+xml", xhtml("Contents", nav)))

    points = []
    for i, (href, _t, content) in enumerate(f for f in files if f[0].endswith(".xhtml") and f[0] != "nav.xhtml"):
        name = re.search(r"<title>(.*?)</title>", content).group(1)
        points.append(f'<navPoint id="n{i + 1}" playOrder="{i + 1}"><navLabel><text>{name}</text></navLabel>'
                      f'<content src="{href}"/></navPoint>')
    ncx = ('<?xml version="1.0" encoding="utf-8"?>\n<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
           f'<head><meta name="dtb:uid" content="{ident}"/></head><docTitle><text>{html.escape(title)}</text></docTitle>'
           f'<navMap>{"".join(points)}</navMap></ncx>')

    manifest, spine = [], []
    for i, (href, media, _c) in enumerate(files):
        props = ' properties="nav"' if href == "nav.xhtml" else ""
        manifest.append(f'<item id="f{i}" href="{href}" media-type="{media}"{props}/>')
        spine.append(f'<itemref idref="f{i}"/>')
    manifest.append('<item id="css" href="style.css" media-type="text/css"/>')
    manifest.append('<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')
    image_names = sorted(n for n in os.listdir(images) if n in conv.boards)
    for n in image_names:
        manifest.append(f'<item id="i{n[1:-4]}" href="images/{n}" media-type="image/png"/>')
    if has_cover:
        manifest.append('<item id="cover" href="cover.jpg" media-type="image/jpeg" properties="cover-image"/>')
    modified = __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime())
    opf = ('<?xml version="1.0" encoding="utf-8"?>\n'
           '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid" xml:lang="en">'
           '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
           f'<dc:identifier id="uid">{ident}</dc:identifier><dc:title>{html.escape(title)}</dc:title>'
           '<dc:creator>Ming Lu</dc:creator><dc:language>en</dc:language>'
           f'<dc:description>{html.escape(band.describe())}</dc:description>'
           f'<meta property="dcterms:modified">{modified}</meta>'
           + ('<meta name="cover" content="cover"/>' if has_cover else "") +
           '</metadata><manifest>' + "".join(manifest) + '</manifest>'
           '<spine toc="ncx">' + "".join(spine) + '</spine></package>')

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with zipfile.ZipFile(out, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml",
                   '<?xml version="1.0" encoding="utf-8"?>\n<container version="1.0" '
                   'xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
                   '<rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
                   '</rootfiles></container>', compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/content.opf", opf, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/toc.ncx", ncx, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/style.css", CSS, compress_type=zipfile.ZIP_DEFLATED)
        for href, _media, content in files:
            z.writestr("OEBPS/" + href, content, compress_type=zipfile.ZIP_DEFLATED)
        for n in image_names:
            z.write(os.path.join(images, n), "OEBPS/images/" + n, compress_type=zipfile.ZIP_STORED)
        if has_cover:
            z.write(cover, "OEBPS/cover.jpg", compress_type=zipfile.ZIP_STORED)
    report = [f"written   {out}  ({len(chapters)} chapters, {len(image_names)} boards, "
              f"{os.path.getsize(out) / 1e6:.1f} MB)"]
    if has_cover:
        report.append(f"written   {cover}  (the cover for KDP: page 1 of the PDF, 1600 x 2560 pixels)")
    else:
        report.append("WARNING   no cover: build the PDF first, the cover is its first page")
    if failed:
        report.append(f"WARNING   {len(failed)} boards could not be drawn: " + ", ".join(failed[:3]))
    return "\n".join(report)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m endgame_book.epub", description="Write the book as an EPUB.")
    add_band_options(parser)
    parser.add_argument("--two-pieces", action="store_true", help="the second book (two pieces a side)")
    args = parser.parse_args(argv)
    band = band_from(args)
    print(write_epub(band, "two" if args.two_pieces else "one"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
