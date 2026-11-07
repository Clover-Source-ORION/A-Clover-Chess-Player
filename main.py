"""CloverChess entry point (first milestone: board display)."""

from board import Board


def main() -> None:
    board = Board.initial_position()
    print("CloverChess — 0x88 board core")
    print(board.display())
    print("\nFEN:", board.to_fen())


if __name__ == "__main__":
    main()
