# CloverChess

A chess engine built from scratch in Python, using only the Python standard library.

## Current milestone: 0x88 board core

Implemented:
- 128-cell 0x88 board representation.
- Algebraic-square / 0x88-index conversion.
- FEN parsing and serialization (six fields).
- Side to move, castling rights, en-passant target and move counters.
- Basic board display.
- Unit tests using Python's built-in `unittest`.

Not implemented yet: move generation, legal-move validation, check detection, evaluation, search, and UCI.

## Run

From this directory:

```bash
python main.py
```

## Run tests

```bash
python -m unittest discover -s tests -v
```

No third-party packages are required.
