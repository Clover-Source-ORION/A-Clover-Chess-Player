"""A transparent, handcrafted evaluation function for CloverChess.

Scores are expressed in centipawns from White's point of view.  This is
intentionally a small, inspectable evaluation rather than a learned model.
"""

from __future__ import annotations

from board import Board, is_on_board

PIECE_VALUES = {
    "p": 100,
    "n": 320,
    "b": 335,
    "r": 500,
    "q": 900,
    "k": 0,
}

MATE_SCORE = 30_000


def _center_bonus(file_index: int, rank_index: int) -> int:
    """Return a small bonus for occupying or controlling the central area."""
    return 14 - abs(2 * file_index - 7) - abs(2 * rank_index - 7)


def _piece_square_bonus(piece: str, file_index: int, rank_index: int,
                        endgame: bool) -> int:
    color = "w" if piece.isupper() else "b"
    kind = piece.lower()
    relative_rank = rank_index if color == "w" else 7 - rank_index
    center = _center_bonus(file_index, rank_index)

    if kind == "p":
        return relative_rank * 7 + center // 2
    if kind == "n":
        return center * 4
    if kind == "b":
        return center * 2
    if kind == "r":
        return (18 if relative_rank == 6 else 0) + (relative_rank * 2)
    if kind == "q":
        return center
    if kind == "k":
        # Keep the king sheltered in the opening; bring it toward the centre
        # once most heavy and minor pieces have disappeared.
        if endgame:
            return center * 5
        edge_shelter = (3 - abs(file_index - 3.5)) * 3
        back_rank = 12 if relative_rank == 0 else 0
        return int(edge_shelter + back_rank - center * 2)
    return 0


def _pawn_structure(board: Board, color: str) -> int:
    """Evaluate doubled, isolated and passed pawns for one side."""
    own_by_file = [0] * 8
    enemy_by_file = [0] * 8
    own_pawns: list[tuple[int, int]] = []
    own_symbol = "P" if color == "w" else "p"
    enemy_symbol = "p" if color == "w" else "P"

    for square in range(128):
        if not is_on_board(square):
            continue
        piece = board.squares[square]
        if piece == own_symbol:
            file_index, rank_index = square & 7, square >> 4
            own_by_file[file_index] += 1
            own_pawns.append((file_index, rank_index))
        elif piece == enemy_symbol:
            enemy_by_file[square & 7] += 1

    score = 0
    for file_index, count in enumerate(own_by_file):
        if count > 1:
            score -= 13 * (count - 1)
        if count and (file_index == 0 or own_by_file[file_index - 1] == 0) \
                and (file_index == 7 or own_by_file[file_index + 1] == 0):
            score -= 11 * count

    for file_index, rank_index in own_pawns:
        passed = True
        for enemy_file in range(max(0, file_index - 1), min(7, file_index + 1) + 1):
            if enemy_by_file[enemy_file]:
                # A black pawn ahead of a white pawn has a smaller rank;
                # a white pawn ahead of a black pawn has a larger rank.
                for enemy_rank in range(8):
                    enemy_square = enemy_rank * 16 + enemy_file
                    if board.squares[enemy_square] == enemy_symbol:
                        if (color == "w" and enemy_rank > rank_index) or \
                                (color == "b" and enemy_rank < rank_index):
                            passed = False
                            break
                if not passed:
                    break
        if passed:
            advance = rank_index if color == "w" else 7 - rank_index
            score += 8 + advance * advance * 3
    return score


def evaluate(board: Board) -> int:
    """Evaluate a position in centipawns from White's point of view."""
    material_phase = 0
    for square in range(128):
        if is_on_board(square):
            piece = board.squares[square]
            if piece:
                material_phase += PIECE_VALUES[piece.lower()] if piece.lower() != "p" else 0
    endgame = material_phase <= 2_600

    score = 0
    white_bishops = 0
    black_bishops = 0
    white_pawns_by_file = [0] * 8
    black_pawns_by_file = [0] * 8

    for square in range(128):
        if not is_on_board(square):
            continue
        piece = board.squares[square]
        if piece is None:
            continue
        kind = piece.lower()
        value = PIECE_VALUES[kind]
        bonus = _piece_square_bonus(piece, square & 7, square >> 4, endgame)
        signed_value = value + bonus
        score += signed_value if piece.isupper() else -signed_value
        if piece == "B":
            white_bishops += 1
        elif piece == "b":
            black_bishops += 1
        elif piece == "P":
            white_pawns_by_file[square & 7] += 1
        elif piece == "p":
            black_pawns_by_file[square & 7] += 1

    if white_bishops >= 2:
        score += 28
    if black_bishops >= 2:
        score -= 28

    score += _pawn_structure(board, "w")
    score -= _pawn_structure(board, "b")

    # Rooks benefit from files without friendly pawns, especially fully open files.
    for square in range(128):
        if not is_on_board(square):
            continue
        piece = board.squares[square]
        if piece is None or piece.lower() != "r":
            continue
        file_index = square & 7
        if white_pawns_by_file[file_index] == 0 and black_pawns_by_file[file_index] == 0:
            bonus = 15
        elif (piece.isupper() and white_pawns_by_file[file_index] == 0) or \
                (piece.islower() and black_pawns_by_file[file_index] == 0):
            bonus = 8
        else:
            bonus = 0
        score += bonus if piece.isupper() else -bonus

    # A small tempo bonus encourages active play without dominating material.
    score += 8 if board.side_to_move == "w" else -8
    return score


def insufficient_material(board: Board) -> bool:
    """Detect common dead-material cases (not every theoretical dead position)."""
    minors: list[tuple[str, int, str]] = []
    for square in range(128):
        if not is_on_board(square):
            continue
        piece = board.squares[square]
        if piece is None or piece.lower() == "k":
            continue
        if piece.lower() in ("p", "r", "q"):
            return False
        minors.append((piece.lower(), ((square >> 4) + (square & 7)) & 1,
                       "w" if piece.isupper() else "b"))

    if not minors:
        return True
    if len(minors) == 1 and minors[0][0] in ("b", "n"):
        return True
    if all(kind == "b" for kind, _, _ in minors):
        # Bishops confined to squares of the same color cannot force mate.
        return len({square_color for _, square_color, _ in minors}) == 1
    return False
