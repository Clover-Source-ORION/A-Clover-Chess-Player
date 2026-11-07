"""Core board representation for CloverChess using 0x88."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from move import Move

FILES = "abcdefgh"
RANKS = "12345678"
PIECES = frozenset("pnbrqkPNBRQK")
INITIAL_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
CASTLING_ORDER = "KQkq"
UNICODE_PIECES = {
    "K": "♔", "Q": "♕", "R": "♖", "B": "♗", "N": "♘", "P": "♙",
    "k": "♚", "q": "♛", "r": "♜", "b": "♝", "n": "♞", "p": "♟",
}


def is_on_board(square: int) -> bool:
    """A square is valid when it is within 0..127 and its 0x88 mask is clear."""
    return isinstance(square, int) and 0 <= square < 128 and (square & 0x88) == 0


def square_to_index(square_name: str) -> int:
    """Convert algebraic coordinates (such as 'e4') to a 0x88 index."""
    if not isinstance(square_name, str) or len(square_name) != 2:
        raise ValueError(f"Invalid square name: {square_name!r}")
    file_name, rank_name = square_name[0].lower(), square_name[1]
    if file_name not in FILES or rank_name not in RANKS:
        raise ValueError(f"Invalid square name: {square_name!r}")
    return (int(rank_name) - 1) * 16 + (ord(file_name) - ord("a"))


def index_to_square(index: int) -> str:
    """Convert a valid 0x88 index to algebraic coordinates."""
    if not is_on_board(index):
        raise ValueError(f"Invalid 0x88 square index: {index!r}")
    return FILES[index & 7] + RANKS[index >> 4]


@dataclass(slots=True)
class UndoState:
    """Information required to reverse one applied move."""

    changed_squares: dict[int, str | None]
    side_to_move: str
    castling_rights: str
    en_passant: int | None
    halfmove_clock: int
    fullmove_number: int


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
            not rights or any(char not in CASTLING_ORDER for char in rights)
            or len(set(rights)) != len(rights)
        ):
            raise ValueError("Invalid castling rights")
        if rights != "-":
            self.castling_rights = "".join(char for char in CASTLING_ORDER if char in rights)

    @classmethod
    def initial_position(cls) -> Board:
        return cls.from_fen(INITIAL_FEN)

    @classmethod
    def from_fen(cls, fen: str) -> Board:
        """Parse the six FEN fields (syntax is checked, reachability is not)."""
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
            if (not castling or any(char not in CASTLING_ORDER for char in castling)
                    or len(set(castling)) != len(castling)):
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

        return cls(squares, active_color, castling_rights, en_passant,
                   halfmove_clock, fullmove_number)

    def to_fen(self) -> str:
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
        return (f"{placement} {self.side_to_move} {castling} {ep_target} "
                f"{self.halfmove_clock} {self.fullmove_number}")

    def piece_at(self, square: int | str) -> str | None:
        index = square_to_index(square) if isinstance(square, str) else square
        if not is_on_board(index):
            raise ValueError(f"Invalid board square: {square!r}")
        return self.squares[index]

    def place_piece(self, square: int | str, piece: str | None) -> None:
        index = square_to_index(square) if isinstance(square, str) else square
        if not is_on_board(index):
            raise ValueError(f"Invalid board square: {square!r}")
        if piece is not None and piece not in PIECES:
            raise ValueError(f"Invalid piece symbol: {piece!r}")
        self.squares[index] = piece

    def make_move(self, move: Move) -> UndoState:
        """Apply a generated move and return a token that can undo it."""
        moving_piece = self.squares[move.start]
        if moving_piece is None:
            raise ValueError("Cannot move from an empty square")

        changed_indices = {move.start, move.end}
        if move.is_en_passant:
            changed_indices.add(move.end - (16 if moving_piece.isupper() else -16))
        rook_from = rook_to = None
        if move.is_castling:
            if move.end > move.start:  # king side
                rook_from, rook_to = move.start + 3, move.start + 1
            else:  # queen side
                rook_from, rook_to = move.start - 4, move.start - 1
            changed_indices.update((rook_from, rook_to))

        undo = UndoState(
            changed_squares={index: self.squares[index] for index in changed_indices},
            side_to_move=self.side_to_move,
            castling_rights=self.castling_rights,
            en_passant=self.en_passant,
            halfmove_clock=self.halfmove_clock,
            fullmove_number=self.fullmove_number,
        )

        captured_piece = self.squares[move.end]
        self.squares[move.start] = None
        if move.is_en_passant:
            captured_square = move.end - (16 if moving_piece.isupper() else -16)
            captured_piece = self.squares[captured_square]
            self.squares[captured_square] = None

        if move.is_castling:
            assert rook_from is not None and rook_to is not None
            self.squares[rook_to] = self.squares[rook_from]
            self.squares[rook_from] = None

        placed_piece = moving_piece
        if move.promotion:
            placed_piece = move.promotion.upper() if moving_piece.isupper() else move.promotion
        self.squares[move.end] = placed_piece

        rights = set(self.castling_rights if self.castling_rights != "-" else "")
        if moving_piece == "K":
            rights.discard("K"); rights.discard("Q")
        elif moving_piece == "k":
            rights.discard("k"); rights.discard("q")
        corner_rights = {0: "Q", 7: "K", 112: "q", 119: "k"}
        if moving_piece in "Rr":
            rights.discard(corner_rights.get(move.start, ""))
        if captured_piece is not None and captured_piece in "Rr":
            rights.discard(corner_rights.get(move.end, ""))
        self.castling_rights = "".join(char for char in CASTLING_ORDER if char in rights) or "-"

        self.en_passant = None
        if moving_piece in "Pp" and abs(move.end - move.start) == 32:
            self.en_passant = (move.start + move.end) // 2

        if moving_piece in "Pp" or captured_piece is not None:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1
        if self.side_to_move == "b":
            self.fullmove_number += 1
        self.side_to_move = "b" if self.side_to_move == "w" else "w"
        return undo

    def unmake_move(self, undo: UndoState) -> None:
        """Restore the exact position saved by make_move."""
        for index, piece in undo.changed_squares.items():
            self.squares[index] = piece
        self.side_to_move = undo.side_to_move
        self.castling_rights = undo.castling_rights
        self.en_passant = undo.en_passant
        self.halfmove_clock = undo.halfmove_clock
        self.fullmove_number = undo.fullmove_number

    def display(self, use_unicode: bool = False) -> str:
        """Return a readable board, optionally using Unicode chess symbols."""
        lines = ["    a  b  c  d  e  f  g  h"]
        lines.append("  +------------------------+")
        for rank in range(7, -1, -1):
            cells = []
            for file_index in range(8):
                piece = self.squares[rank * 16 + file_index]
                if piece is None:
                    cells.append("·" if use_unicode else ".")
                else:
                    cells.append(UNICODE_PIECES[piece] if use_unicode else piece)
            lines.append(f"{rank + 1} | " + "  ".join(cells) + f" | {rank + 1}")
        lines.append("  +------------------------+")
        lines.append("    a  b  c  d  e  f  g  h")
        side = "White" if self.side_to_move == "w" else "Black"
        lines.append(f"Turn: {side}    Castling: {self.castling_rights}    En passant: "
                     f"{'-' if self.en_passant is None else index_to_square(self.en_passant)}")
        lines.append(f"Halfmove clock: {self.halfmove_clock}    Fullmove: {self.fullmove_number}")
        return "\n".join(lines)


if __name__ == "__main__":
    board = Board.initial_position()
    print(board.display(use_unicode=True))
    print("\nFEN:", board.to_fen())
