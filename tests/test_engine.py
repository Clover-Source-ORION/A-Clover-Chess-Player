import unittest

from board import Board
from engine import Searcher
from evaluation import evaluate, insufficient_material
from movegen import generate_legal_moves


class EvaluationTests(unittest.TestCase):
    def test_starting_position_is_near_equal(self):
        board = Board.initial_position()
        self.assertLessEqual(abs(evaluate(board)), 10)

    def test_evaluation_changes_after_queen_is_removed(self):
        even = Board.from_fen("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
        queen_up = Board.from_fen("4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1")
        self.assertGreater(evaluate(queen_up), evaluate(even) + 800)

    def test_insufficient_material(self):
        self.assertTrue(insufficient_material(Board.from_fen("4k3/8/8/8/8/8/8/4K3 w - - 0 1")))
        self.assertTrue(insufficient_material(Board.from_fen("4k3/8/8/8/8/8/8/3NK3 w - - 0 1")))
        self.assertFalse(insufficient_material(Board.initial_position()))


class SearchTests(unittest.TestCase):
    def test_engine_returns_a_legal_move_and_preserves_board(self):
        board = Board.initial_position()
        original_fen = board.to_fen()
        result = Searcher().search(board, max_depth=2, time_limit=1.0)
        self.assertIsNotNone(result.move)
        self.assertIn(result.move, generate_legal_moves(board))
        self.assertGreaterEqual(result.depth, 1)
        self.assertGreater(result.nodes, 0)
        self.assertEqual(board.to_fen(), original_fen)

    def test_finds_mate_in_one(self):
        board = Board.from_fen("7k/8/5KQ1/8/8/8/8/8 w - - 0 1")
        result = Searcher().search(board, max_depth=3, time_limit=1.0)
        self.assertEqual(result.move.uci(), "g6g7")
        self.assertGreaterEqual(result.score, 29_000)

    def test_takes_a_hanging_queen_when_in_check(self):
        board = Board.from_fen("4k3/8/8/8/8/8/4q3/4K2R w - - 0 1")
        result = Searcher().search(board, max_depth=3, time_limit=1.0)
        self.assertEqual(result.move.uci(), "e1e2")

    def test_terminal_position_returns_no_move(self):
        board = Board.from_fen("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
        result = Searcher().search(board, max_depth=2, time_limit=0.2)
        self.assertIsNone(result.move)

    def test_checkmate_root_is_reported_as_a_loss(self):
        board = Board.from_fen("7k/6Q1/5K2/8/8/8/8/8 b - - 1 1")
        result = Searcher().search(board, max_depth=2, time_limit=0.2)
        self.assertIsNone(result.move)
        self.assertLessEqual(result.score, -29_000)

    def test_fifty_move_draw_claim_stops_search(self):
        board = Board.from_fen("4k3/8/8/8/8/8/8/4K2R w - - 100 50")
        result = Searcher().search(board, max_depth=2, time_limit=0.2)
        self.assertIsNone(result.move)
        self.assertEqual(result.score, 0)

    def test_search_rejects_invalid_limits(self):
        searcher = Searcher()
        with self.assertRaises(ValueError):
            searcher.search(Board.initial_position(), max_depth=0)
        with self.assertRaises(ValueError):
            searcher.search(Board.initial_position(), time_limit=0)


if __name__ == "__main__":
    unittest.main()
