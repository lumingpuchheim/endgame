"""Checks on the lines of moves in your comments, for the report after a build.

Two problems are found:
- a line with no statement: a sentence that is only moves, and nothing after it says what the line
  leads to (who is better, and why). Example: "The bishop must be activated. 48.Kg2."
- a correction that ends with the other side's move and says nothing about the result: when your
  note is on a mistake (39.Rb5?) and shows the better move for the same side (39.Rb1 ...), the line
  must either end with a move of that side or be followed by a clear statement ("83.Kh1! g2+ 84.Kg1
  Kg3 is stalemate" is fine). Other lines (the opponent's tries, refutations) are not checked.
  Example: on 39.Rb5?, "39.Rb1 h5 40.Rf1 Kb7 41.Rf8 g5 42.Rf5 h4 43.Rxg5 h3" ends with Black.

A line is a run of moves with at least one move number ("39.", "39..."), as you write them in notes/."""

import re
from typing import List, Optional, Tuple

_SAN = r"(?:O-O(?:-O)?|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?)[+#]?[!?]*"
_NUMBERED = re.compile(r"(\d+)\.(\.\.)?\s*(" + _SAN + r")(?![\w])")
_NEXT = re.compile(r"\s+(?:(\d+)\.(\.\.)?\s*)?(" + _SAN + r")(?![\w])")


def plain(text: str) -> str:
    """Your LaTeX as the reader sees the words: figures as letters, index entries left out."""
    text = text.replace("\\#", "#")                                      # 25.Qe8\# is mate
    text = re.sub(r"\\(?:index|indexonly|label|cite)\{[^{}]*\}", "", text)
    text = re.sub(r"\\termas\{[^{}]*\}\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\term\{([^{}]*)\}", lambda m: m.group(1).replace("-", " "), text)
    text = re.sub(r"\\xref\{([^{}]*)\}\{[^{}]*\}", r"\1 X", text)
    text = re.sub(r"\\([KQRBN])(?:\{\})?\s*(?=x|[a-h]|[1-8][a-hx])", r"\1", text)     # \K e5 -> Ke5
    text = re.sub(r"\\([KQRBN])(?:\{\})?", r"\1", text)                       # e8=\Q{} -> e8=Q
    text = re.sub(r"\\[a-zA-Z]+\*?", " ", text).replace("{", "").replace("}", "").replace("~", " ")
    return text


def runs_of_moves(text: str) -> List[Tuple[int, int, List[Tuple[int, bool, str]]]]:
    """[(start, end, [(move number, White's move, move as written), ...]), ...] for each line in text."""
    out, pos = [], 0
    while True:
        m = _NUMBERED.search(text, pos)
        if not m:
            return out
        number, white = int(m.group(1)), m.group(2) is None
        moves, end = [(number, white, m.group(3))], m.end()
        while True:
            n = _NEXT.match(text, end)
            if not n:
                break
            if n.group(1):                                  # a new move number: trust it
                number, white = int(n.group(1)), n.group(2) is None
            else:                                           # the other side's move
                if not white:
                    number += 1
                white = not white
            moves.append((number, white, n.group(3)))
            end = n.end()
        out.append((m.start(), end, moves))
        pos = end


def move_name(number: int, white: bool, san: str) -> str:
    return f"{number}.{'' if white else '..'}{san}"


def lines_of_moves(text: str) -> List[Tuple[int, int, str, str, int]]:
    """[(start, end, first move, last move, plies), ...]; moves written as '39.Rb1' and '43...h3'."""
    return [(start, end, move_name(*moves[0]), move_name(*moves[-1]), len(moves))
            for start, end, moves in runs_of_moves(text)]


def bare_move(san: str) -> str:
    """The move without its mark and check sign, to compare a move in your line with the game's."""
    return re.sub(r"[+#?!]+$", "", san)


def _sentences(text: str) -> List[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def problems(comment: str, correction: Optional[Tuple[bool, int]] = None) -> List[str]:
    """What is wrong with the lines of one comment (one note as printed), in plain words.
    correction: (White to move, move number) when the note is on a mistake: a line from that move
    shows the better move. If nothing says what it leads to, it must end with a move of the same side."""
    text = plain(comment)
    runs = lines_of_moves(text)
    marked, pieces, pos = [], [], 0
    for start, end, first, last, _p in runs:                # each line becomes one placeholder
        pieces += [text[pos:start], f"\x00{len(marked)}\x00"]
        marked.append((first, last))
        pos = end
    pieces.append(text[pos:])
    sentences = _sentences("".join(pieces))
    bare = [not re.sub(r"\x00\d+\x00|[\s.,;:!?()\[\]'\"-]|\b(and|or|then)\b", "", s) and "\x00" in s
            for s in sentences]
    out = []
    for i, sentence in enumerate(sentences):        # a sentence of moves only, with no statement after it
        if not (bare[i] and (i == len(sentences) - 1 or bare[i + 1])):
            continue
        ids = [int(x) for x in re.findall(r"\x00(\d+)\x00", sentence)]
        found = []
        for n in ids:
            _start, _end, first, last, plies = runs[n]
            number, rest = first.split(".", 1)
            white = not rest.startswith("..")
            refutation = re.search(r"[^?!](\?\??|\?!)$", first)     # another bad try: its reply is the point
            if correction == (white, int(number)) and plies % 2 == 0 and not refutation:
                side = "White" if white else "Black"
                found.append(f"line {first} ... {last} corrects {side}'s mistake but ends with the other side's "
                             "move, and nothing says what it leads to")
        if not found:
            first, last = marked[ids[0]][0], marked[ids[-1]][1]
            shown = first if first == last else f"{first} ... {last}"
            found.append(f"line {shown} says nothing about what it leads to (who is better, and why)")
        out += found
    return out
