"""Perft utilities used to validate CloverChess move generation."""

from board import Board
from movegen import generate_legal_moves


def perft(board: Board, depth: int) -> int:
    """Count leaf positions reached in *depth* plies."""
    if depth < 0:
        raise ValueError("Perft depth cannot be negative")
    if depth == 0:
        return 1
    nodes = 0
    for move in generate_legal_moves(board):
        undo = board.make_move(move)
        nodes += perft(board, depth - 1)
        board.unmake_move(undo)
    return nodes


def perft_divide(board: Board, depth: int) -> dict[str, int]:
    """Return the node count below each legal root move."""
    if depth < 1:
        raise ValueError("Perft divide depth must be at least one")
    results: dict[str, int] = {}
    for move in generate_legal_moves(board):
        undo = board.make_move(move)
        results[move.uci()] = perft(board, depth - 1)
        board.unmake_move(undo)
    return results
