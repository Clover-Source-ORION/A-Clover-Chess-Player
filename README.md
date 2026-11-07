# CloverChess

A chess engine project built from scratch in Python. The board representation is **0x88** and the code uses only Python's standard library. No third-party chess package or engine is used.

## Current milestone: 0.2 — complete legal move generation and graphical interface

Implemented:
- 128-cell 0x88 board and algebraic-coordinate conversion.
- FEN parsing and serialization (six fields).
- Move representation in UCI coordinate notation.
- Pawn, knight, bishop, rook, queen and king movement.
- Castling, promotion and en-passant.
- Attack detection, check detection and legal-move filtering.
- Reversible move application (`make_move` / `unmake_move`).
- Perft and perft-divide utilities.
- Interactive local two-player terminal interface with Unicode pieces.
- Clickable graphical interface built with Python standard-library Tkinter: select/move pieces, legal-move hints, move history, undo, board flip, promotion selection, and FEN load/copy.
- Commands: `moves`, `fen`, `undo`, `new`, `perft N`, `help`, `quit`.
- Checkmate and stalemate detection through legal-move exhaustion plus check detection.
- 25 unit tests, including known Perft reference positions.

Not implemented yet:
- Position evaluation and an AI opponent.
- Search (Negamax, Alpha-Beta, iterative deepening, quiescence).
- Transposition tables and move-ordering heuristics.
- UCI protocol for GUI / external-engine matches.

## Project structure

```text
CloverChess/
├── board.py          # 0x88 board, FEN, make/unmake, display
├── move.py           # Move data structure and UCI notation
├── movegen.py        # Pseudo-legal/legal moves and attack detection
├── perft.py          # Move-generation validation
├── main.py           # Terminal entry point and GUI launcher
├── gui.py            # Tkinter graphical interface
├── tests/
│   ├── test_board.py
│   └── test_movegen.py
└── README.md
```

## Run

```bash
python main.py
```

Launch the graphical board (Tkinter is part of Python's standard library; the Python installation must include Tcl/Tk):

```bash
python main.py --gui
```

Use ASCII symbols if the terminal does not render chess Unicode symbols:

```bash
python main.py --ascii
```

Start from a custom FEN:

```bash
python main.py --fen "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
```

Moves are entered as coordinate strings, e.g. `e2e4`, `g1f3`, or `e7e8q` for promotion.

## Run tests

```bash
python -m unittest discover -s tests -v
```

## Perft validation

In the interactive game, run `perft 3` to count all legal move sequences three plies deep. The initial position must return:

| Depth | Nodes |
|---:|---:|
| 1 | 20 |
| 2 | 400 |
| 3 | 8,902 |
| 4 | 197,281 |

No third-party packages are required.

The move generator is correct against the tested Perft reference positions, but it is not yet optimized for engine-strength search. CloverChess is still a rules-and-interface foundation: it does not yet evaluate positions or choose moves autonomously.
