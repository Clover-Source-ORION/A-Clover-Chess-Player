import unittest

from board import (
    Board,
    INITIAL_FEN,
    index_to_square,
    is_on_board,
    square_to_index,
)


class SquareConversionTests(unittest.TestCase):
    def test_known_indices(self):
        self.assertEqual(square_to_index("a1"), 0)
        self.assertEqual(square_to_index("h1"), 7)
        self.assertEqual(square_to_index("a2"), 16)
        self.assertEqual(square_to_index("e4"), 52)
        self.assertEqual(square_to_index("h8"), 119)

    def test_round_trip_all_64_squares(self):
        for rank in "12345678":
            for file_name in "abcdefgh":
                square = file_name + rank
                self.assertEqual(index_to_square(square_to_index(square)), square)

    def test_0x88_offboard_detection(self):
        self.assertTrue(is_on_board(0))
        self.assertTrue(is_on_board(119))
        self.assertFalse(is_on_board(8))
        self.assertFalse(is_on_board(15))
        self.assertFalse(is_on_board(128))
        self.assertFalse(is_on_board(-1))

    def test_invalid_coordinates(self):
        for square in ("i4", "a9", "e0", "e", "e44", "z2"):
            with self.subTest(square=square):
                with self.assertRaises(ValueError):
                    square_to_index(square)


class BoardTests(unittest.TestCase):
    def test_initial_position_matches_standard_fen(self):
        board = Board.initial_position()
        self.assertEqual(board.to_fen(), INITIAL_FEN)
        self.assertEqual(board.piece_at("e1"), "K")
        self.assertEqual(board.piece_at("e8"), "k")
        self.assertEqual(board.piece_at("e4"), None)

    def test_fen_round_trip_with_en_passant_and_counters(self):
        fen = "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3"
        board = Board.from_fen(fen)
        self.assertEqual(board.to_fen(), fen)
        self.assertEqual(board.en_passant, square_to_index("d6"))
        self.assertEqual(board.fullmove_number, 3)

    def test_castling_rights_are_serialized_in_canonical_order(self):
        fen = "8/8/8/8/8/8/8/8 w qK - 0 1"
        self.assertEqual(Board.from_fen(fen).to_fen(), "8/8/8/8/8/8/8/8 w Kq - 0 1")

    def test_place_and_clear_piece(self):
        board = Board()
        board.place_piece("c4", "N")
        self.assertEqual(board.piece_at("c4"), "N")
        board.place_piece("c4", None)
        self.assertIsNone(board.piece_at("c4"))

    def test_invalid_fen_is_rejected(self):
        invalid_fens = (
            "8/8/8/8/8/8/8 w - - 0 1",  # only seven ranks
            "8/8/8/8/8/8/8/9 w - - 0 1",  # rank too wide
            "8/8/8/8/8/8/8/7X w - - 0 1",  # unknown piece
            "8/8/8/8/8/8/8/8 x - - 0 1",  # invalid active color
            "8/8/8/8/8/8/8/8 w KK - 0 1",  # duplicate castling right
            "8/8/8/8/8/8/8/8 w - - -1 1",  # negative halfmove clock
        )
        for fen in invalid_fens:
            with self.subTest(fen=fen):
                with self.assertRaises(ValueError):
                    Board.from_fen(fen)


if __name__ == "__main__":
    unittest.main()
