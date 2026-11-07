"""Core board representation for CloverChess.

The board uses the 0x88 representation:
    a1 = 0, b1 = 1, ..., h1 = 7
    a2 = 16, ..., h8 = 119

A square is on the board exactly when (square & 0x88) == 0.
Only Python's standard library is used.
"""

from __future__ import annotations

from dataclasses import dataclass, field


FILES = "abcdefgh"
RANKS = "12345678"
PIECES = frozenset("pnbrqkPNBRQK")
INITIAL_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
CASTLING_ORDER = "KQkq"


def is_on_board(square: int) -> bool:
    """Return True if *square* is a valid 0x88 board index."""
    return isinstance(square, int) and 0 <= square < 128 and (square & 0x88) == 0


def square_to_index(square_name: str) -> int:
    """Convert algebraic coordinates (for example, 'e4') to a 0x88 index."""
    if not isinstance(square_name, str) or len(square_name) != 2:
        raise ValueError(f"Invalid square name: {square_name!r}")

    file_name, rank_name = square_name[0].lower(), square_name[1]
    if file_name not in FILES or rank_name not in RANKS:
        raise ValueError(f"Invalid square name: {square_name!r}")

    file_index = ord(file_name) - ord("a")
    rank_index = int(rank_name) - 1
    return rank_index * 16 + file_index


def index_to_square(index: int) -> str:
    """Convert a valid 0x88 index to algebraic coordinates."""
    if not is_on_board(index):
        raise ValueError(f"Invalid 0x88 square index: {index!r}")

    file_name = FILES[index & 0x07]
    rank_name = RANKS[index >> 4]
    return file_name + rank_name


@dataclass(slots=True)
class Board:
    """A chess position stored in a 128-entry 0x88 array."""

    squares: list[str | None] = field(default_factory=lambda: [None] * 128)
    side_to_move: str = "w"
    castling_rights: str = "KQkq"
    en_passant: int | None = None
    halfmove_clock: int = 0
    fullmove_number: int = 1

    def __post_init__(self) -> None:
        if len(self.squares) != 128:
            raise ValueError("A 0x88 board must contain exactly 128 entries")
        if self.side_to_move not in ("w", "b"):
            raise ValueError("side_to_move must be 'w' or 'b'")
        if any(piece is not None and piece not in PIECES for piece in self.squares):
            raise ValueError("Board contains an unknown piece symbol")
        if self.en_passant is not None and not is_on_board(self.en_passant):
            raise ValueError("en_passant must be None or a valid board square")
        if self.halfmove_clock < 0:
            raise ValueError("halfmove_clock cannot be negative")
        if self.fullmove_number < 1:
            raise ValueError("fullmove_number must be at least 1")

        rights = self.castling_rights
        if rights != "-" and (
            not rights
            or any(char not in CASTLING_ORDER for char in rights)
            or len(set(rights)) != len(rights)
        ):
            raise ValueError("Invalid castling rights")
        if rights != "-":
            self.castling_rights = "".join(char for char in CASTLING_ORDER if char in rights)

    @classmethod
    def initial_position(cls) -> Board:
        """Create the standard starting position."""
        return cls.from_fen(INITIAL_FEN)

    @classmethod
    def from_fen(cls, fen: str) -> Board:
        """Create a board from a six-field FEN string.

        This validates FEN structure and field syntax. It does not prove that
        the represented position is reachable or legal in a chess game.
        """
        if not isinstance(fen, str):
            raise ValueError("FEN must be a string")

        fields = fen.strip().split()
        if len(fields) != 6:
            raise ValueError("FEN must contain exactly six fields")

        placement, active_color, castling, ep_target, halfmove, fullmove = fields
        ranks = placement.split("/")
        if len(ranks) != 8:
            raise ValueError("FEN piece placement must contain eight ranks")

        squares: list[str | None] = [None] * 128
        for fen_rank, rank_text in enumerate(ranks):
            file_index = 0
            board_rank = 7 - fen_rank

            for symbol in rank_text:
                if symbol in "12345678":
                    file_index += int(symbol)
                elif symbol in PIECES:
                    if file_index >= 8:
                        raise ValueError("FEN rank contains more than eight files")
                    squares[board_rank * 16 + file_index] = symbol
                    file_index += 1
                else:
                    raise ValueError(f"Invalid FEN piece-placement symbol: {symbol!r}")

                if file_index > 8:
                    raise ValueError("FEN rank contains more than eight files")

            if file_index != 8:
                raise ValueError("Each FEN rank must describe exactly eight files")

        if active_color not in ("w", "b"):
            raise ValueError("FEN active color must be 'w' or 'b'")

        if castling == "-":
            castling_rights = "-"
        else:
            if (
                not castling
                or any(char not in CASTLING_ORDER for char in castling)
                or len(set(castling)) != len(castling)
            ):
                raise ValueError("Invalid FEN castling field")
            castling_rights = "".join(char for char in CASTLING_ORDER if char in castling)

        en_passant = None if ep_target == "-" else square_to_index(ep_target)
        try:
            halfmove_clock = int(halfmove)
            fullmove_number = int(fullmove)
        except ValueError as exc:
            raise ValueError("FEN move counters must be integers") from exc

        if halfmove_clock < 0 or fullmove_number < 1:
            raise ValueError("Invalid FEN move counters")

        return cls(
            squares=squares,
            side_to_move=active_color,
            castling_rights=castling_rights,
            en_passant=en_passant,
            halfmove_clock=halfmove_clock,
            fullmove_number=fullmove_number,
        )

    def to_fen(self) -> str:
        """Serialize the current position to a six-field FEN string."""
        fen_ranks: list[str] = []

        for rank in range(7, -1, -1):
            empty_count = 0
            rank_text = ""

            for file_index in range(8):
                piece = self.squares[rank * 16 + file_index]
                if piece is None:
                    empty_count += 1
                else:
                    if empty_count:
                        rank_text += str(empty_count)
                        empty_count = 0
                    rank_text += piece

            if empty_count:
                rank_text += str(empty_count)
            fen_ranks.append(rank_text)

        placement = "/".join(fen_ranks)
        castling = self.castling_rights or "-"
        ep_target = "-" if self.en_passant is None else index_to_square(self.en_passant)
        return (
            f"{placement} {self.side_to_move} {castling} {ep_target} "
            f"{self.halfmove_clock} {self.fullmove_number}"
        )

    def piece_at(self, square: int | str) -> str | None:
        """Return the piece on a square, or None when it is empty."""
        index = square_to_index(square) if isinstance(square, str) else square
        if not is_on_board(index):
            raise ValueError(f"Invalid board square: {square!r}")
        return self.squares[index]

    def place_piece(self, square: int | str, piece: str | None) -> None:
        """Place a piece on a square. Pass None to clear the square."""
        index = square_to_index(square) if isinstance(square, str) else square
        if not is_on_board(index):
            raise ValueError(f"Invalid board square: {square!r}")
        if piece is not None and piece not in PIECES:
            raise ValueError(f"Invalid piece symbol: {piece!r}")
        self.squares[index] = piece

    def display(self) -> str:
        """Return a human-readable board, with rank 8 at the top."""
        lines = ["  +-----------------+"]
        for rank in range(7, -1, -1):
            cells = []
            for file_index in range(8):
                piece = self.squares[rank * 16 + file_index]
                cells.append(piece if piece is not None else ".")
            lines.append(f"{rank + 1} | " + " ".join(cells) + " |")
        lines.append("  +-----------------+")
        lines.append("    a b c d e f g h")
        lines.append(f"Side to move: {'White' if self.side_to_move == 'w' else 'Black'}")
        lines.append(f"Castling: {self.castling_rights}")
        lines.append(
            "En passant: "
            + ("-" if self.en_passant is None else index_to_square(self.en_passant))
        )
        lines.append(f"Halfmove: {self.halfmove_clock} | Fullmove: {self.fullmove_number}")
        return "\n".join(lines)


if __name__ == "__main__":
    board = Board.initial_position()
    print(board.display())
    print("\nFEN:", board.to_fen())
