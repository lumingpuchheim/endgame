"""Wording used in the book. Everything a reader sees that the program writes is here.

'chapter <<label>>' in a text becomes a clickable cross reference (\\xref{chapter}{label})."""

import datetime
from typing import List, Optional, Tuple

from .stats import Row, Summary

PIECE_NAMES = {"Q": "queen", "R": "rook", "B": "bishop", "N": "knight"}
NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight",
                9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}


def _side(side: str) -> str:
    """'RB' -> 'rook and bishop', 'RR' -> 'two rooks', 'pawns' -> 'pawns'."""
    if side == "pawns":
        return "pawns"
    names = []
    for letter in "QRBN":
        count = side.count(letter)
        if count == 1:
            names.append(PIECE_NAMES[letter])
        elif count > 1:
            names.append(f"{NUMBER_WORDS.get(count, count)} {PIECE_NAMES[letter]}s")
    return " and ".join(names)


def material_name(key: str) -> str:
    """'R v R' -> 'Rook vs rook', 'pawns v pawns' -> 'King and pawns', 'R v pawns' -> 'Rook vs pawns'."""
    if key == "B v B same":
        return "Bishop vs bishop, same colour"
    if key == "B v B opposite":
        return "Bishop vs bishop, opposite colours"
    a, _, b = key.partition(" v ")
    if a == b == "pawns":
        return "King and pawns"
    text = f"{_side(a)} vs {_side(b)}"
    return text[0].upper() + text[1:]


def _with_pawns(pieces: str, pawns: int) -> str:
    name = _side(pieces) if pieces else "king"
    if pawns == 0:
        return name
    return f"{name} and " + ("pawn" if pawns == 1 else f"{NUMBER_WORDS.get(pawns, pawns)} pawns")


def section_title(section) -> str:
    """Title of a chapter section: a pawn balance, or the merged section with many pawns. When both
    sides have the same pieces, the chapter title already names them, so only the pawns are counted:
    'Two pawns vs one' instead of 'Rook and two pawns vs rook and pawn'."""
    from .sections import MANY
    if section == MANY:
        return "Three or more pawns on one side"
    (pieces_a, pawns_a), (pieces_b, pawns_b) = section
    if pieces_a != pieces_b:
        return pawns_title(section)
    words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}
    count = lambda n: f"{words.get(n, n)} pawn{'s' if n != 1 else ''}"
    if pawns_a == 0:
        text = "no pawns"
    elif pawns_a == pawns_b:
        text = f"{count(pawns_a)} each"
    elif pawns_b == 0:
        text = f"{count(pawns_a)} vs none"
    else:
        text = f"{count(pawns_a)} vs {words.get(pawns_b, pawns_b)}"
    return text[0].upper() + text[1:]


def pawns_title(split) -> str:
    """Section title from sections.pawn_split: (('R', 2), ('R', 0)) -> 'Rook and two pawns vs rook',
    (('R', 1), ('R', 1)) -> 'Rook and pawn vs rook and pawn'."""
    (pieces_a, pawns_a), (pieces_b, pawns_b) = split
    text = f"{_with_pawns(pieces_a, pawns_a)} vs {_with_pawns(pieces_b, pawns_b)}"
    return text[0].upper() + text[1:]


def players(s: Summary) -> str:
    """'rated 1500–1599 (average of both players)', for use inside a sentence."""
    text = s.band.describe()
    return text[0].lower() + text[1:]


# --- Part I ------------------------------------------------------------------

COMMON_TITLE = "How Often Each Endgame Comes Up"
TRICKY_TITLE = "How Often Each Endgame Goes Wrong"


def common_intro(s: Summary, book_only: bool = False) -> List[str]:
    scope = (" Only the endgames this book covers are shown, the same ones in all three charts of this part."
             if book_only else "")
    return [
        "Before choosing what to study, it helps to know what you will actually meet over the board. "
        f"This chapter counts, in all {s.games:,} games of players {players(s)}, how often each endgame came "
        "up. These are numbers from the games, not from the positions in this book." + scope,
        "Each bar is one material balance, whoever has which side: “Rook vs rook” counts every "
        "game in which each side had a rook (and pawns). A game that passes through several endgames "
        "counts once for each of them.",
    ]


def common_points(rows: List[Row]) -> List[str]:
    if not rows:
        return []
    top = rows[:3]
    points = [f"{material_name(top[0].key)} is the endgame you will meet most: it came up in "
              f"{top[0].per_100_games:.0f} of every 100 games."]
    if len(top) > 1:
        rest = ", ".join(f"{material_name(r.key).lower()} ({r.per_100_games:.0f})" for r in top[1:])
        points.append(f"Next come {rest}.")
    return points


def tricky_intro(s: Summary, min_games: int, book_only: bool = False) -> List[str]:
    rule = ("" if book_only else f" Endgames that came up in fewer than {min_games:,} games are left out: "
            "with fewer games, chance decides the order.")
    return [
        "Some endgames are harder than others. This chapter asks: once an endgame is on the board, how "
        "often does a player throw away half a point or more? Again, these are numbers from all the games.",
        "A blunder here is a move that turns a win into a draw or a loss, or a draw into a loss, while a "
        "better move was available. The bar shows how many such moves were made per 100 games that "
        "reached the endgame." + rule,
    ]


def tricky_points(rows: List[Row]) -> List[str]:
    if not rows:
        return []
    top = rows[0]
    points = [f"{material_name(top.key)} is the hardest to handle: {top.blunders_per_100:.0f} blunders per "
              "100 games that reach it."]
    if len(rows) > 2:
        points.append("Endgames that are hard to play are not always the ones you meet often. "
                      "Chapter <<ch:where-to-start>> puts both together.")
    return points


def overall_intro() -> List[str]:
    return [
        "An endgame deserves your study time if it comes up often and goes wrong often. This chapter "
        "multiplies the two: how many blunders each endgame causes per 100 games played, whether the "
        "game reached that endgame or not.",
        "Read the chart from the top. The endgames there cost players the most half points, so "
        "they come first in the rest of the book.",
    ]


def tricky_empty(s: Summary, min_games: int) -> str:
    """Chapter 2 without a chart: no endgame came up often enough in this band yet."""
    return (f"None of the endgames came up in at least {min_games:,} of these {s.games:,} games yet, so none is "
            "ranked here. The ranking follows once more games of this band are annotated.")


def no_chapters_yet(games: int, needed: int) -> str:
    """Part II of a band with too few games for endgame chapters."""
    return (f"This band has only {games:,} annotated games so far. That is too few to choose good positions "
            f"for the endgame chapters, so they follow once at least {needed:,} games of this band are annotated.")


def overall_points(rows: List[Row], has_chapters: bool = True,
                   book_order: Optional[List[str]] = None, left_out: Optional[str] = None) -> List[str]:
    """book_order: the materials of Part II's chapters in their order, when the book has them."""
    if not rows:
        return []
    order = ", then ".join(material_name(r.key).lower() for r in rows[:3])
    first = (f"{material_name(rows[0].key)} alone causes {rows[0].blunders_per_100_all:.0f} blunders per 100 "
             "games played.")
    starts = book_order[0] if book_order else rows[0].key
    if rows[0].key == "R v R" and has_chapters and starts == "R v R":
        first += " Part <<part:endgames>> starts there."
    points = [f"Study in this order: {order}.", first]
    if has_chapters and book_order:
        example = f", such as {material_name(left_out).lower()}," if left_out else ""
        points.append(f"This book does not cover every endgame, and that is on purpose. It covers the "
                      f"{len(book_order)} endgames in the chart, the ones that cost the most half points. The "
                      f"others{example} come up rarely or go wrong seldom: the time you would spend on them is "
                      "better spent here.")
        if "pawns v pawns" in book_order:
            points.append(simple_first_text(True))
    return points


def simple_first_text(has_pawns: bool) -> str:
    """Why Part II puts the king and pawn endings first, whatever they cost. Empty without them."""
    if not has_pawns:
        return ""
    return ("Part <<part:endgames>> changes this order in one way: it starts with king and pawn endings, the "
            "simplest of all, however many points they cost. Every other endgame can turn into one, and its "
            "ideas build on them. After that, the order above stays: the endgame that costs the most points "
            "comes first.")


# --- Appendix ----------------------------------------------------------------

def data_lines(s: Summary) -> List[Tuple[str, str]]:
    share = s.games_with_endgame / s.games * 100 if s.games else 0
    if not s.sources:
        files = "-"
    elif len(s.sources) == 1:
        files = s.sources[0]
    else:
        files = f"{s.sources[0]} to {s.sources[-1]} ({len(s.sources)} files)"
    return [
        ("Games", f"{s.games:,} over-the-board games from The Week in Chess, {players(s)}"),
        ("Source files", files),
        ("Games reaching an endgame" if not s.book else "Games reaching these endgames",
         f"{s.games_with_endgame:,} ({share:.0f}%)"),
        ("Endgames in this book", BOOK_ENDGAMES[s.book]) if s.book else ("Endgame rule", s.endgame_rule),
        ("Engine", f"Stockfish, depth {s.depth}"),
        ("Blunders counted", f"{s.real_blunders:,}" if s.book else f"{s.real_blunders:,} of {s.marked_blunders:,} marked"),
        ("Numbers made on", datetime.date.today().isoformat()),
    ]


BOOK_ENDGAMES = {
    "one": "King and pawns, and the endgames where each side has at most one piece (queen, rook, bishop or knight)",
    "two": "The endgames where one side or both have two pieces, and neither side more than two (queens, rooks, "
           "bishops, knights)",
}


def definitions(min_games: int, book: str = "") -> List[Tuple[str, str]]:
    endgame = {"one": "A position where each side has at most one piece besides king and pawns (a queen, a rook, "
                      "a bishop or a knight), or only king and pawns.",
               "two": "A position where one side or both have two pieces besides king and pawns, and neither side "
                      "more than two (queens, rooks, bishops, knights)."}.get(book, "A position where each side has at most the number of pieces in the "
                                             "endgame rule (queens, rooks, bishops, knights; kings and pawns not counted).")
    return [
        ("Endgame", endgame),
        ("Material", "The pieces each side has, whoever has which: “Rook and bishop vs rook and "
                     "knight” counts both colours. A game counts once for each material it reaches."),
        ("Exchanges", "A material counts only once it stands for at least 2 moves (one by each side). "
                      "Shorter states in the middle of an exchange belong to the material before them."),
        ("Winning", "At least +1.50 for one side in Stockfish's score; below that the position counts as equal."),
        ("Blunder", "A move after which the mover drops from winning to equal, from equal to losing, or "
                    "from winning to losing, while the engine's best move was a different move and at "
                    "least one move kept the result. Marked moves that fail this test are engine noise "
                    "near the 1.50 line, not mistakes."),
        ("Per 100 games that reach it", "Blunders made in this material, per 100 games that reached it (chapter <<ch:go-wrong>>)."),
        ("Per 100 games played", "Blunders made in this material per 100 games in the data, whether or not "
                                 "they reached it: how often it happens times how often it goes wrong (chapter <<ch:where-to-start>>)."),
        ("Ranking", f"Only materials reached in at least {min_games:,} games are ranked in chapter <<ch:go-wrong>>. "
                    "With fewer games, splitting the data in two halves gave a different top of the list."),
    ]


# --- Part II: one chapter per endgame -------------------------------------------

ERRORS_ATTACKER = "a win thrown away"
ERRORS_DEFENDER = "a draw lost"
ERRORS_AXIS = "share of the commented positions"


def errors_intro() -> str:
    """The paragraph above a chapter's chart of typical technical errors."""
    return ("The typical technical errors of this ending. Each bar shows how often the idea decided a "
            "position: the share of this chapter's commented positions that turn on it, split into wins thrown "
            "away and draws lost. These are the things to watch for at the board.")


NAMED_IDEAS = ("Berger", "Bähr", "Lucena", "Philidor", "Vancura", "Ponziani", "Réti", "Saavedra", "Troitzky")


def _lower(idea: str) -> str:
    """'Cut-off' -> 'cut-off' in the middle of a sentence; ideas named after a player keep their capital."""
    if idea.startswith(NAMED_IDEAS):
        return idea
    return idea[0].lower() + idea[1:]


def errors_summary(rows) -> str:
    """Words for the chart: which ideas decide most positions, and who misses them.
    rows: (idea, % attacker, % defender), most frequent first."""
    if not rows:
        return ""
    share = lambda r: r[1] + r[2]
    top = rows[:3]
    names = [f"{_lower(r[0])} ({share(r):.0f}%)" for r in top]
    listed = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
    text = [f"The ideas that decide most positions here are {listed}."]
    attacker = [_lower(r[0]) for r in rows if share(r) >= 10 and r[1] >= 0.75 * share(r)]
    defender = [_lower(r[0]) for r in rows if share(r) >= 10 and r[2] >= 0.75 * share(r)]
    join = lambda xs: xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]
    if attacker:
        text.append(f"The stronger side above all misses {join(attacker)}: watch for "
                    f"{'it' if len(attacker) == 1 else 'them'} when you are winning.")
    if defender:
        text.append(f"The defender above all misses {join(defender)}: watch for "
                    f"{'it' if len(defender) == 1 else 'them'} when you have to hold a draw.")
    return " ".join(text)


BASICS_TITLE = "What You Need from the Simpler Endings"


def basics_intro() -> List[str]:
    return ["The endgames in this book often turn into simpler ones, and many of their ideas come from the "
            "endings with one piece a side. This chapter collects what you need from those endings, sorted by "
            "the kind of ending each idea comes from, so that the chapters after it can stay with the endgames "
            "of this book.",
            "When a comment later uses one of these ideas, it gives the page where the idea is explained here. "
            "If you know it already, read on; if not, look it up."]


EPILOGUE_TITLE = "Epilogue: What to Pay Attention To"


def epilogue_intro(positions: int, chapters: int) -> List[str]:
    return ["Most endgame books tell you what is important because the author, or the tradition, says so. "
            "This book tries something else: it counts. Every position in it comes from real games between "
            "players of your strength, and in each one a player went wrong. The comments name the idea that would "
            "have saved the game. Counting these ideas over the whole book shows what actually decides games at "
            "this level. Ideas that come up often are worth your time first; ideas that never come up can wait, "
            "however famous they are.",
            f"This book has {positions} commented positions in {chapters} chapters. The counting rests on three "
            "things you should know. The positions and the mistakes come from the games and from Stockfish, but "
            "which idea a mistake shows is the author's judgement; another annotator might file some positions "
            "differently. The positions are a selection: about 30 per chapter, chosen from many more. And small "
            "numbers are rough: a difference of one or two positions means little, only the clear leaders mean "
            "something.",
            "The ideas are of two kinds, and they are counted separately. Technical ideas belong to a certain "
            "ending: a cut-off in rook endings, a fork with the knight, the wrong bishop and the rook's pawn. "
            "They can be learned once and recognised again. General ideas, such as the process of elimination or "
            "prophylaxis, are ways of thinking that help in every position; almost any position could be filed "
            "under them."]


def epilogue_technical(rows, places) -> str:
    """rows: (idea, % attacker, % defender); places: idea -> chapter titles where it matters most."""
    if not rows:
        return ""
    lines = [errors_summary(rows), "The five most frequent are marked ‘Top idea’ in the margin of the "
                                   "comments, at their first mention in each chapter."]
    ending = lambda title: title.lower().replace(", same colour", " (same colour)").replace(
        ", opposite colours", " (opposite colours)")
    named = [f"{_lower(r[0])} in {_join([ending(p) for p in places.get(r[0], [])])}" for r in rows[:3]
             if places.get(r[0])]
    if named:
        lines.append("They come up mostly in these endings: " + "; ".join(named) + ".")
    return " ".join(lines)


def epilogue_general(rows) -> str:
    if not rows:
        return ""
    share = lambda r: r[1] + r[2]
    names = [f"{_lower(r[0])} ({share(r):.0f}%)" for r in rows[:3]]
    return (f"Among the general ideas, {_join(names)} come up most often. They do not replace knowing the "
            "endings, but they are how a player finds the right move when no rule tells him what to do.")


def epilogue_closing() -> str:
    return "These are the ideas that cost points in real games. Learn them first."


def _join(xs: List[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def chapter_intro(row: Row, rank: int) -> List[str]:
    """Opening paragraphs of an endgame chapter."""
    name = material_name(row.key)
    return [
        f"{name} came up in {row.per_100_games:.1f} of every 100 games. Once it was on the board, "
        f"players blundered {row.blunders_per_100:.0f} times per 100 games (chapter <<ch:go-wrong>>). It is "
        f"number {rank} among the endgames of this book in the order of study (chapter <<ch:where-to-start>>).",
        "The positions below are taken from the games this book is built from. In each "
        "one, the player to move went wrong. They are ordered from the fewest pawns on the board to the "
        "most, so the first sections hold the cleanest examples.",
        "Before you read the moves, cover them and find the right move yourself. Then read on: the mistake "
        "is marked with ?, and the rest of the game shows what happened. If a game reaches a position you "
        "have already seen, the book says so and stops there.",
    ]
