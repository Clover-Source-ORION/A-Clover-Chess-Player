"""CloverChess terminal interface. Uses only the Python standard library."""

from __future__ import annotations

import argparse

from board import Board
from movegen import find_legal_move, generate_legal_moves, is_in_check
from perft import perft


def print_help() -> None:
    print("""
Commands:
  e2e4       Play a move using coordinate notation
  e7e8q      Promote a pawn (q, r, b or n)
  moves      List all legal moves
  fen        Show the current FEN position
  undo       Take back the last move
  perft N    Count legal move sequences to depth N
  new        Start a new game
  help       Show this help
  quit       Exit CloverChess
""")


def game_loop(board: Board, use_unicode: bool = True) -> None:
    history = []
    print("CloverChess 0.2 — local two-player chess")
    print("Enter 'help' to see available commands. Moves use UCI coordinate notation.")

    while True:
        print("\n" + board.display(use_unicode=use_unicode))
        legal_moves = generate_legal_moves(board)
        checked = is_in_check(board)

        if not legal_moves:
            if checked:
                winner = "Black" if board.side_to_move == "w" else "White"
                print(f"\nCHECKMATE — {winner} wins!")
            else:
                print("\nSTALEMATE — draw.")
            break
        if checked:
            print("CHECK!")

        side = "White" if board.side_to_move == "w" else "Black"
        try:
            command = input(f"\n{side}> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCloverChess closed.")
            break
        if not command:
            continue

        lowered = command.lower()
        if lowered in ("quit", "exit", "q"):
            print("CloverChess closed.")
            break
        if lowered in ("help", "?"):
            print_help()
            continue
        if lowered == "fen":
            print(board.to_fen())
            continue
        if lowered == "moves":
            print("Legal moves:", " ".join(move.uci() for move in legal_moves))
            continue
        if lowered == "undo":
            if history:
                move, undo = history.pop()
                board.unmake_move(undo)
                print("Undid", move.uci())
            else:
                print("There are no moves to undo.")
            continue
        if lowered == "new":
            board = Board.initial_position()
            history.clear()
            print("New game started.")
            continue
        if lowered.startswith("perft "):
            try:
                depth = int(lowered.split()[1])
                if not 0 <= depth <= 4:
                    raise ValueError
                print(f"Perft depth {depth}: {perft(board, depth):,} nodes")
            except (ValueError, IndexError):
                print("Usage: perft N (N must be between 0 and 4).")
            continue

        move = find_legal_move(board, command)
        if move is None:
            print("Illegal or unrecognized move. Use 'moves' or 'help'.")
            continue
        undo = board.make_move(move)
        history.append((move, undo))
        print("Played:", move.uci())


def main() -> None:
    parser = argparse.ArgumentParser(description="CloverChess — a from-scratch Python chess project")
    parser.add_argument("--fen", help="Start from a supplied six-field FEN position")
    parser.add_argument("--ascii", action="store_true", help="Use ASCII pieces instead of Unicode symbols")
    parser.add_argument("--gui", action="store_true", help="Launch the Tkinter graphical interface")
    args = parser.parse_args()

    try:
        board = Board.from_fen(args.fen) if args.fen else Board.initial_position()
    except ValueError as exc:
        parser.error(f"Invalid FEN: {exc}")

    if args.gui:
        try:
            from gui import run_gui
            run_gui(initial_fen=board.to_fen())
        except ImportError as exc:
            parser.error(f"Tkinter is not available in this Python installation: {exc}")
    else:
        game_loop(board, use_unicode=not args.ascii)


if __name__ == "__main__":
    main()
