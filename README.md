# CloverChess

A from-scratch chess engine written in Python. CloverChess uses a **0x88 board representation** and only Python's standard library. It does not use `python-chess`, NumPy, an external chess engine, a neural network, or an opening database.

## Current milestone: 0.3 — first thinking engine

CloverChess can now choose and play moves by searching future variations.

### The engine's brain

- **Handcrafted evaluation** (`evaluation.py`): material, piece-square activity, king placement for opening/endgame, bishop pair, rook files, and pawn structure (doubled, isolated and passed pawns).
- **Negamax with Alpha-Beta pruning** (`engine.py`): explores the game tree while pruning branches that cannot improve the current result.
- **Iterative deepening**: completes depth 1, then 2, then 3, and so on. If the time limit expires, it returns the best move from the last completed depth.
- **Quiescence search**: extends tactical capture sequences at the horizon to reduce the horizon effect.
- **Transposition table**: remembers previously searched positions and their bounds.
- **Move ordering**: transposition-table move, captures ordered with a victim/attacker score, promotions, killer moves and history heuristic.
- **Draw handling in search**: 50-move clock, common insufficient-material cases, and threefold repetition within the current search line.
- **Time-bounded search**: configurable maximum depth and time per move.

This is a classical search engine, not a database lookup. Chess's enormous game-tree estimate is not something we try to store. CloverChess calculates a manageable slice of the tree from the current position and evaluates the resulting positions.

### Play against CloverChess

Graphical interface (Tkinter is part of Python's standard library):

```bash
python main.py --gui
```

The GUI starts in **Play White (vs CloverChess)** mode. You can choose to play Black instead, or switch to Two Players. Engine strengths:

- Quick: depth up to 3, about 0.45 seconds per move.
- Standard: depth up to 4, about 1.35 seconds per move.
- Strong: depth up to 5, about 3 seconds per move.

The depth is a maximum, not a guarantee. The engine returns the last fully completed iteration when its time limit is reached. Its search runs in a worker thread, so the graphical interface remains responsive. The GUI reports depth, nodes, nodes per second, score and principal variation.

Terminal game against CloverChess as Black:

```bash
python main.py --vs-ai
```

Change the search budget:

```bash
python main.py --vs-ai --ai-depth 5 --ai-time 3.0
```

Ask for a suggestion during a two-player terminal game with `hint`, or let CloverChess play the current side with `go`.

Local two-player terminal game:

```bash
python main.py
```

Start from a custom six-field FEN:

```bash
python main.py --fen "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
```

Use ASCII pieces if the terminal does not render chess Unicode symbols:

```bash
python main.py --ascii
```

## Project structure

```text
CloverChess/
├── board.py          # 0x88 board, FEN, reversible make/unmake
├── move.py           # Move data structure and UCI notation
├── movegen.py        # Legal moves, attacks, checks, special moves
├── perft.py          # Move-generation validation
├── evaluation.py     # Handcrafted positional evaluation
├── engine.py         # Negamax, Alpha-Beta, quiescence, TT, ordering
├── main.py           # Terminal entry point and AI play mode
├── gui.py            # Tkinter GUI and human-vs-engine mode
└── tests/
    ├── test_board.py
    ├── test_movegen.py
    └── test_engine.py
```

## Run tests

```bash
python -m unittest discover -s tests -v
```

The test suite includes board/FEN tests, move-generation tests and Perft reference positions, plus engine tests for legal move selection, position preservation, mate-in-one, capturing a checking queen, evaluation and terminal positions.

## Current limitations / next work

CloverChess 0.3 is a functioning first AI, not yet a strong tournament engine. Search is still Python-level and modest-depth; the evaluation is handcrafted and deliberately simple. Search-line repetition is detected, but the engine does not yet receive the complete game history for full game-level repetition adjudication.

Planned improvements:

1. Improve evaluation (mobility, king safety, threats, pawn terms and tapered phase scores).
2. Improve search (aspiration windows, principal-variation search, check extensions, better pruning and faster move generation).
3. Add a proper UCI protocol so CloverChess can play Stockfish through an external chess GUI.
4. Build a match-testing harness and measure strength over many games, rather than judging it by a few positions.

No external Python packages are required. Tkinter must be included in the local Python installation for the graphical interface.
