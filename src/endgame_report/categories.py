"""Endgame categories: every material belongs to exactly one, by the rules below.

Material is colour-neutral: the two sides are compared, not White and Black.
'Pieces' are queens, rooks, bishops and knights; kings and pawns are not counted.
'Minor pieces' are bishops and knights.
"""

from typing import List, Tuple

# (key, name, rule, examples) in the order the report lists them.
CATEGORIES: List[Tuple[str, str, str, str]] = [
    ("pawns", "Pawns only", "Neither side has a piece.", "pawns v pawns"),
    ("pieces_vs_pawns", "Pieces vs pawns", "One side has pieces, the other has none.", "R v pawns, B v pawns"),
    ("q_v_q", "Queen vs queen", "Each side has a queen and nothing else.", "Q v Q"),
    ("queens_equal", "Queens with more pieces", "Each side has a queen plus the same number of other pieces.",
     "QR v QR, QB v QN, QRB v QRN"),
    ("queens_unequal", "Queens, unequal pieces", "Each side has a queen; the number of other pieces differs.",
     "Q v QR, QR v QRB"),
    ("queen_vs_none", "Queen vs no queen", "Exactly one side has a queen.", "QR v RR, Q v RB, QB v R"),
    ("r_v_r", "Rook vs rook", "Each side has one rook and nothing else.", "R v R"),
    ("rr_v_rr", "Two rooks each", "Each side has two rooks and nothing else.", "RR v RR"),
    ("rm_v_rm", "Rook and minor piece each", "Each side has one rook and one minor piece.",
     "RB v RN, RB v RB, RN v RN"),
    ("rrm_v_rrm", "Two rooks and minor piece each", "Each side has two rooks and one minor piece.",
     "RRB v RRN, RRB v RRB"),
    ("rmm_v_rmm", "Rook and two minor pieces each", "Each side has one rook and two minor pieces.",
     "RBN v RBN, RBB v RBN"),
    ("rooks_unequal", "Rooks, unequal pieces",
     "Both sides have a rook and no queen; the number of rooks or of minor pieces differs.",
     "R v RB, RB v RRB, R v RR, RN v RBN"),
    ("rook_vs_minors", "Rooks vs minor pieces", "No queens; exactly one side has rooks.", "R v B, RB v BN, R v BB"),
    ("b_v_b_same", "Bishop vs bishop, same colour", "One bishop each, on squares of the same colour.", "B v B"),
    ("b_v_b_opposite", "Bishop vs bishop, opposite colours", "One bishop each, on squares of different colours.",
     "B v B"),
    ("n_v_n", "Knight vs knight", "One knight each.", "N v N"),
    ("b_v_n", "Bishop vs knight", "One side a bishop, the other a knight.", "B v N"),
    ("minors_more", "Minor pieces, two on a side", "Only minor pieces; at least one side has two or more.",
     "BN v BN, BB v BN, B v BN"),
    ("other", "Other", "Anything not covered above (for example three rooks each).", "RRR v RRR"),
]

NAMES = {key: name for key, name, _, _ in CATEGORIES}
ORDER = {key: i for i, (key, _, _, _) in enumerate(CATEGORIES)}


def _count(side: str) -> Tuple[int, int, int]:
    """(queens, rooks, minor pieces) of one side, e.g. 'RRB' -> (0, 2, 1)."""
    return side.count("Q"), side.count("R"), side.count("B") + side.count("N")


def category(signature: str, kind: str) -> str:
    """Category key for a signature like 'RN-RB'. `kind` is the annotation's EgTypes value
    (needed only to tell same-coloured from opposite-coloured bishops)."""
    a, b = (signature.split("-", 1) + [""])[:2]
    if not a and not b:
        return "pawns"
    if not a or not b:
        return "pieces_vs_pawns"
    (qa, ra, ma), (qb, rb, mb) = _count(a), _count(b)
    if qa and qb:
        if ra == rb == ma == mb == 0:
            return "q_v_q"
        return "queens_equal" if (ra + ma) == (rb + mb) else "queens_unequal"
    if qa or qb:
        return "queen_vs_none"
    if ra and rb:
        if (ra, ma) != (rb, mb):
            return "rooks_unequal"
        return {(1, 0): "r_v_r", (2, 0): "rr_v_rr", (1, 1): "rm_v_rm",
                (2, 1): "rrm_v_rrm", (1, 2): "rmm_v_rmm"}.get((ra, ma), "other")
    if ra or rb:
        return "rook_vs_minors"
    if ma == mb == 1:
        if a == b == "B":
            return "b_v_b_opposite" if kind == "bishop_opposite" else "b_v_b_same"
        if a == b == "N":
            return "n_v_n"
        return "b_v_n"
    return "minors_more"
