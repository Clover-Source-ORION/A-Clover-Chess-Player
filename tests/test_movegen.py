import unittest

from board import Board
from movegen import (
    find_king,
    find_legal_move,
    generate_legal_moves,
    generate_pseudo_legal_moves,
    is_in_check,
    is_square_attacked,
)
from perft import perft


class MoveGenerationTests(unittest.TestCase):
    def test_initial_position_has_20_legal_moves(self):
        board = Board.initial_position()
        self.assertEqual(len(generate_legal_moves(board)), 20)

    def test_initial_position_perft_depths_one_to_three(self):
        board = Board.initial_position()
        original_fen = board.to_fen()
        self.assertEqual(perft(board, 1), 20)
        self.assertEqual(perft(board, 2), 400)
        self.assertEqual(perft(board, 3), 8902)
        self.assertEqual(board.to_fen(), original_fen)

    def test_knight_moves_from_center(self):
        board = Board.from_fen("4k3/8/8/8/3N4/8/8/4K3 w - - 0 1")
        moves = {move.uci() for move in generate_legal_moves(board)}
        self.assertEqual(sum(move.startswith("d4") for move in moves), 8)

    def test_sliding_pieces_stop_at_blockers(self):
        board = Board.from_fen("4k3/8/8/8/3R4/3p4/8/4K3 w - - 0 1")
        moves = {move.uci() for move in generate_pseudo_legal_moves(board)}
        self.assertIn("d4d3", moves)  # capture the pawn
        self.assertNotIn("d4d2", moves)  # cannot move through it

    def test_pawn_double_step_and_capture(self):
        board = Board.initial_position()
        moves = {move.uci() for move in generate_legal_moves(board)}
        self.assertIn("e2e3", moves)
        self.assertIn("e2e4", moves)
        self.assertNotIn("e2e5", moves)

    def test_promotion_generates_all_four_choices(self):
        board = Board.from_fen("4k3/P7/8/8/8/8/8/4K3 w - - 0 1")
        moves = {move.uci() for move in generate_legal_moves(board)}
        self.assertTrue({"a7a8q", "a7a8r", "a7a8b", "a7a8n"}.issubset(moves))

    def test_en_passant_is_generated_and_applied(self):
        board = Board.from_fen("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
        move = find_legal_move(board, "e5d6")
        self.assertIsNotNone(move)
        undo = board.make_move(move)
        self.assertEqual(board.piece_at("d6"), "P")
        self.assertIsNone(board.piece_at("d5"))
        board.unmake_move(undo)
        self.assertEqual(board.piece_at("e5"), "P")
        self.assertEqual(board.piece_at("d5"), "p")

    def test_castling_both_sides_and_rook_relocation(self):
        board = Board.from_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
        moves = {move.uci(): move for move in generate_legal_moves(board)}
        self.assertIn("e1g1", moves)
        self.assertIn("e1c1", moves)
        undo = board.make_move(moves["e1g1"])
        self.assertEqual(board.piece_at("g1"), "K")
        self.assertEqual(board.piece_at("f1"), "R")
        self.assertNotIn("K", board.castling_rights)
        board.unmake_move(undo)
        self.assertEqual(board.to_fen(), "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")

    def test_castling_through_attacked_square_is_forbidden(self):
        board = Board.from_fen("4kr2/8/8/8/8/8/8/4K2R w K - 0 1")
        moves = {move.uci() for move in generate_legal_moves(board)}
        self.assertNotIn("e1g1", moves)

    def test_check_detection_and_pinned_piece_legality(self):
        board = Board.from_fen("8/8/8/8/8/4k3/4r3/4K3 w - - 0 1")
        self.assertTrue(is_in_check(board))
        self.assertTrue(is_square_attacked(board, find_king(board, "w"), "b"))
        moves = {move.uci() for move in generate_legal_moves(board)}
        self.assertTrue(all(not move.startswith("e1e2") for move in moves))

    def test_en_passant_that_exposes_king_is_illegal(self):
        board = Board.from_fen("4k3/8/8/r4pPK/8/8/8/8 w - f6 0 1")
        moves = {move.uci() for move in generate_legal_moves(board)}
        self.assertNotIn("g5f6", moves)

    def test_king_cannot_move_into_check(self):
        board = Board.from_fen("4r1k1/8/8/8/8/8/8/4K3 w - - 0 1")
        moves = {move.uci() for move in generate_legal_moves(board)}
        self.assertNotIn("e1e2", moves)

    def test_checkmate_and_stalemate_positions(self):
        checkmate = Board.from_fen("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")
        self.assertTrue(is_in_check(checkmate))
        self.assertEqual(generate_legal_moves(checkmate), [])

        stalemate = Board.from_fen("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
        self.assertFalse(is_in_check(stalemate))
        self.assertEqual(generate_legal_moves(stalemate), [])

    def test_kiwipete_perft_depths_one_and_two(self):
        board = Board.from_fen("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1")
        self.assertEqual(perft(board, 1), 48)
        self.assertEqual(perft(board, 2), 2039)

    def test_famous_endgame_perft_position(self):
        board = Board.from_fen("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1")
        self.assertEqual(perft(board, 1), 14)
        self.assertEqual(perft(board, 2), 191)
        self.assertEqual(perft(board, 3), 2812)

    def test_additional_reference_positions(self):
        reference_cases = (
            ("r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1", 6, 264),
            ("rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8", 44, 1486),
            ("r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10", 46, 2079),
        )
        for fen, depth_one, depth_two in reference_cases:
            with self.subTest(fen=fen):
                board = Board.from_fen(fen)
                self.assertEqual(perft(board, 1), depth_one)
                self.assertEqual(perft(board, 2), depth_two)


if __name__ == "__main__":
    unittest.main()
