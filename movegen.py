"""Move generation and attack detection for CloverChess (0x88)."""

from __future__ import annotations

from board import Board, is_on_board, square_to_index
from move import Move

KNIGHT_OFFSETS = (33, 31, 18, 14, -14, -18, -31, -33)
KING_OFFSETS = (16, 1, -16, -1, 15, 17, -15, -17)
BISHOP_OFFSETS = (15, 17, -15, -17)
ROOK_OFFSETS = (16, -16, 1, -1)
QUEEN_OFFSETS = BISHOP_OFFSETS + ROOK_OFFSETS
PROMOTION_PIECES = ("q", "r", "b", "n")


def piece_color(piece: str) -> str:
    return "w" if piece.isupper() else "b"


def opposite(color: str) -> str:
    return "b" if color == "w" else "w"


def find_king(board: Board, color: str) -> int | None:
    king = "K" if color == "w" else "k"
    for square in range(128):
        if is_on_board(square) and board.squares[square] == king:
            return square
    return None


def is_square_attacked(board: Board, square: int, by_color: str) -> bool:
    """Return whether *square* is attacked by a piece of *by_color*."""
    if not is_on_board(square):
        raise ValueError("Attack target must be on the board")

    # Pawn source squares are the reverse of the pawn's attack direction.
    pawn = "P" if by_color == "w" else "p"
    pawn_sources = (square - 15, square - 17) if by_color == "w" else (square + 15, square + 17)
    for source in pawn_sources:
        if is_on_board(source) and board.squares[source] == pawn:
            return True

    knight = "N" if by_color == "w" else "n"
    for offset in KNIGHT_OFFSETS:
        source = square + offset
        if is_on_board(source) and board.squares[source] == knight:
            return True

    king = "K" if by_color == "w" else "k"
    for offset in KING_OFFSETS:
        source = square + offset
        if is_on_board(source) and board.squares[source] == king:
            return True

    bishop, rook, queen = (("B", "R", "Q") if by_color == "w" else ("b", "r", "q"))
    for directions, attackers in ((BISHOP_OFFSETS, (bishop, queen)),
                                  (ROOK_OFFSETS, (rook, queen))):
        for direction in directions:
            target = square + direction
            while is_on_board(target):
                piece = board.squares[target]
                if piece is not None:
                    if piece in attackers:
                        return True
                    break
                target += direction
    return False


def is_in_check(board: Board, color: str | None = None) -> bool:
    """Return whether the requested side (default: side to move) is in check."""
    color = color or board.side_to_move
    king_square = find_king(board, color)
    # Incomplete analysis/test positions can omit kings; they are not treated as checked.
    if king_square is None:
        return False
    return is_square_attacked(board, king_square, opposite(color))


def _add_pawn_move(moves: list[Move], start: int, end: int, promotion_rank: int) -> None:
    if (end >> 4) == promotion_rank:
        moves.extend(Move(start, end, promotion=piece) for piece in PROMOTION_PIECES)
    else:
        moves.append(Move(start, end))


def generate_pseudo_legal_moves(board: Board) -> list[Move]:
    """Generate moves obeying piece movement, but not necessarily king safety."""
    color = board.side_to_move
    enemy = opposite(color)
    moves: list[Move] = []

    for start in range(128):
        if not is_on_board(start):
            continue
        piece = board.squares[start]
        if piece is None or piece_color(piece) != color:
            continue
        kind = piece.lower()

        if kind == "p":
            direction = 16 if color == "w" else -16
            start_rank = 1 if color == "w" else 6
            promotion_rank = 7 if color == "w" else 0
            one = start + direction
            if is_on_board(one) and board.squares[one] is None:
                _add_pawn_move(moves, start, one, promotion_rank)
                two = start + 2 * direction
                if (start >> 4) == start_rank and board.squares[two] is None:
                    moves.append(Move(start, two))
            for offset in (direction - 1, direction + 1):
                target = start + offset
                if not is_on_board(target):
                    continue
                target_piece = board.squares[target]
                if target_piece is not None and piece_color(target_piece) == enemy:
                    if target_piece.lower() != "k":
                        _add_pawn_move(moves, start, target, promotion_rank)
                elif target == board.en_passant:
                    captured_square = target - direction
                    expected_pawn = "p" if color == "w" else "P"
                    if board.squares[captured_square] == expected_pawn:
                        moves.append(Move(start, target, is_en_passant=True))

        elif kind == "n":
            for offset in KNIGHT_OFFSETS:
                target = start + offset
                if not is_on_board(target):
                    continue
                target_piece = board.squares[target]
                if target_piece is None or (piece_color(target_piece) == enemy and target_piece.lower() != "k"):
                    moves.append(Move(start, target))

        elif kind in ("b", "r", "q"):
            directions = BISHOP_OFFSETS if kind == "b" else ROOK_OFFSETS if kind == "r" else QUEEN_OFFSETS
            for direction in directions:
                target = start + direction
                while is_on_board(target):
                    target_piece = board.squares[target]
                    if target_piece is None:
                        moves.append(Move(start, target))
                    else:
                        if piece_color(target_piece) == enemy and target_piece.lower() != "k":
                            moves.append(Move(start, target))
                        break
                    target += direction

        elif kind == "k":
            for offset in KING_OFFSETS:
                target = start + offset
                if not is_on_board(target):
                    continue
                target_piece = board.squares[target]
                if target_piece is None or (piece_color(target_piece) == enemy and target_piece.lower() != "k"):
                    moves.append(Move(start, target))

            # Castling is generated only from the orthodox king start square.
            if color == "w" and start == square_to_index("e1"):
                if "K" in board.castling_rights and board.squares[5] is None and board.squares[6] is None \
                        and board.squares[7] == "R" \
                        and not is_square_attacked(board, 4, "b") \
                        and not is_square_attacked(board, 5, "b") \
                        and not is_square_attacked(board, 6, "b"):
                    moves.append(Move(4, 6, is_castling=True))
                if "Q" in board.castling_rights and board.squares[1] is None and board.squares[2] is None \
                        and board.squares[3] is None and board.squares[0] == "R" \
                        and not is_square_attacked(board, 4, "b") \
                        and not is_square_attacked(board, 3, "b") \
                        and not is_square_attacked(board, 2, "b"):
                    moves.append(Move(4, 2, is_castling=True))
            elif color == "b" and start == square_to_index("e8"):
                if "k" in board.castling_rights and board.squares[117] is None and board.squares[118] is None \
                        and board.squares[119] == "r" \
                        and not is_square_attacked(board, 116, "w") \
                        and not is_square_attacked(board, 117, "w") \
                        and not is_square_attacked(board, 118, "w"):
                    moves.append(Move(116, 118, is_castling=True))
                if "q" in board.castling_rights and board.squares[113] is None and board.squares[114] is None \
                        and board.squares[115] is None and board.squares[112] == "r" \
                        and not is_square_attacked(board, 116, "w") \
                        and not is_square_attacked(board, 115, "w") \
                        and not is_square_attacked(board, 114, "w"):
                    moves.append(Move(116, 114, is_castling=True))

    return moves


def generate_legal_moves(board: Board) -> list[Move]:
    """Generate all moves that leave the moving side's king safe."""
    moving_side = board.side_to_move
    legal: list[Move] = []
    for move in generate_pseudo_legal_moves(board):
        undo = board.make_move(move)
        safe = not is_in_check(board, moving_side)
        board.unmake_move(undo)
        if safe:
            legal.append(move)
    return legal


def find_legal_move(board: Board, uci_text: str) -> Move | None:
    """Find a legal move matching UCI coordinate input, case-insensitively."""
    text = uci_text.strip().lower()
    if len(text) not in (4, 5):
        return None
    try:
        start = square_to_index(text[:2])
        end = square_to_index(text[2:4])
    except ValueError:
        return None
    promotion = text[4] if len(text) == 5 else None
    for move in generate_legal_moves(board):
        if move.start == start and move.end == end and move.promotion == promotion:
            return move
    return None
