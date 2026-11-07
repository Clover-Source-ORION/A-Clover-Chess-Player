"""Move representation for CloverChess. No third-party dependencies."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Move:
    """A chess move using 0x88 square indices.

    promotion is one of q/r/b/n (always lowercase internally).
    Special-move flags are stored explicitly so make/unmake is unambiguous.
    """

    start: int
    end: int
    promotion: str | None = None
    is_en_passant: bool = False
    is_castling: bool = False

    def __post_init__(self) -> None:
        if self.promotion is not None and self.promotion not in "qrbn":
            raise ValueError("Promotion must be one of q, r, b or n")

    @staticmethod
    def _square_name(square: int) -> str:
        if not (0 <= square < 128 and (square & 0x88) == 0):
            raise ValueError(f"Invalid 0x88 square index: {square}")
        return chr(ord("a") + (square & 7)) + str((square >> 4) + 1)

    def uci(self) -> str:
        """Return coordinate notation, e.g. e2e4 or e7e8q."""
        result = self._square_name(self.start) + self._square_name(self.end)
        return result + (self.promotion or "")

    def __str__(self) -> str:
        return self.uci()
