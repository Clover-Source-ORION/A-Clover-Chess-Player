"""CloverChess search engine: Negamax, alpha-beta, quiescence and TT.

Uses only CloverChess modules and Python's standard library.
"""

from __future__ import annotations

from dataclasses import dataclass
import time

from board import Board
from evaluation import MATE_SCORE, PIECE_VALUES, evaluate, insufficient_material
from move import Move
from movegen import generate_legal_moves, is_in_check

INFINITY = 32_000
MATE_THRESHOLD = MATE_SCORE - 1_000
MAX_PLY = 96
QUIESCENCE_LIMIT = 10

EXACT = 0
LOWER_BOUND = 1
UPPER_BOUND = 2


@dataclass(slots=True)
class TTEntry:
    depth: int
    score: int
    flag: int
    best_move: Move | None


@dataclass(frozen=True, slots=True)
class SearchResult:
    move: Move | None
    score: int
    depth: int
    nodes: int
    elapsed: float
    principal_variation: tuple[str, ...]

    @property
    def nodes_per_second(self) -> int:
        return int(self.nodes / self.elapsed) if self.elapsed > 0 else 0


class _SearchTimeout(Exception):
    pass


def _repetition_key(board: Board) -> str:
    """A repetition key: piece placement, side, castling and en-passant state."""
    pieces = "".join(
        board.squares[square] or "."
        for square in range(128) if (square & 0x88) == 0
    )
    ep = "-" if board.en_passant is None else str(board.en_passant)
    return pieces + board.side_to_move + board.castling_rights + ep


def _position_key(board: Board) -> str:
    """A transposition key including the halfmove clock, but not fullmove number."""
    return _repetition_key(board) + str(min(board.halfmove_clock, 100))


def _captured_piece(board: Board, move: Move) -> str | None:
    if move.is_en_passant:
        captured_square = move.end - (16 if board.side_to_move == "w" else -16)
        return board.squares[captured_square]
    return board.squares[move.end]


class Searcher:
    """Iterative-deepening chess searcher with reusable transpositions."""

    def __init__(self, max_tt_entries: int = 250_000) -> None:
        self.max_tt_entries = max_tt_entries
        self.transposition_table: dict[str, TTEntry] = {}
        self.killers: dict[int, list[Move]] = {}
        self.history_heuristic: dict[tuple[str, str, int], int] = {}
        self.nodes = 0
        self.qnodes = 0
        self.deadline = 0.0
        self._path_counts: dict[str, int] = {}
        self._pv: list[list[Move]] = [[] for _ in range(MAX_PLY)]

    def clear_hash(self) -> None:
        self.transposition_table.clear()

    def search(self, board: Board, max_depth: int = 5,
               time_limit: float = 1.0) -> SearchResult:
        """Find a move, returning the last fully completed iterative-deepening pass."""
        if max_depth < 1:
            raise ValueError("max_depth must be at least 1")
        if time_limit <= 0:
            raise ValueError("time_limit must be positive")

        started = time.perf_counter()
        self.deadline = started + time_limit
        self.nodes = 0
        self.qnodes = 0
        self.killers.clear()
        self.history_heuristic.clear()
        self._pv = [[] for _ in range(MAX_PLY)]

        legal_moves = generate_legal_moves(board)
        if not legal_moves:
            return SearchResult(None, -MATE_SCORE if is_in_check(board) else 0,
                                0, 0, time.perf_counter() - started, ())
        if board.halfmove_clock >= 100 or insufficient_material(board):
            return SearchResult(None, 0, 0, 0, time.perf_counter() - started, ())

        fallback = legal_moves[0]
        best_move = fallback
        best_score = self._evaluate_for_side(board)
        completed_depth = 0
        best_pv: tuple[str, ...] = (fallback.uci(),)
        self._path_counts = {_repetition_key(board): 1}

        for depth in range(1, max_depth + 1):
            self._pv = [[] for _ in range(MAX_PLY)]
            try:
                score, move, pv = self._search_root(board, depth, best_move)
            except _SearchTimeout:
                break
            if move is not None:
                best_move = move
                best_score = score
                completed_depth = depth
                best_pv = tuple(item.uci() for item in pv) or (move.uci(),)
            if abs(best_score) >= MATE_THRESHOLD:
                break

        elapsed = time.perf_counter() - started
        return SearchResult(best_move, best_score, completed_depth,
                            self.nodes, elapsed, best_pv)

    def _check_time(self) -> None:
        if time.perf_counter() >= self.deadline:
            raise _SearchTimeout

    def _evaluate_for_side(self, board: Board) -> int:
        score = evaluate(board)
        return score if board.side_to_move == "w" else -score

    def _search_root(self, board: Board, depth: int,
                     previous_best: Move | None) -> tuple[int, Move | None, list[Move]]:
        alpha = -INFINITY
        beta = INFINITY
        best_score = -INFINITY
        best_move = None
        moves = self._order_moves(board, generate_legal_moves(board), previous_best, 0)
        if not moves:
            return (-MATE_SCORE if is_in_check(board) else 0), None, []

        for move in moves:
            self._check_time()
            undo = board.make_move(move)
            repetition_key = _repetition_key(board)
            self._path_counts[repetition_key] = self._path_counts.get(repetition_key, 0) + 1
            try:
                score = -self._negamax(board, depth - 1, -beta, -alpha, 1)
            finally:
                self._path_counts[repetition_key] -= 1
                if self._path_counts[repetition_key] == 0:
                    del self._path_counts[repetition_key]
                board.unmake_move(undo)

            if score > best_score:
                best_score = score
                best_move = move
                best_line = self._pv[1][:]
                self._pv[0] = [move] + best_line
            if score > alpha:
                alpha = score

        return best_score, best_move, self._pv[0][:]

    def _negamax(self, board: Board, depth: int, alpha: int, beta: int,
                 ply: int) -> int:
        self.nodes += 1
        if (self.nodes & 0xFF) == 0:
            self._check_time()
        if ply >= MAX_PLY - 1:
            return self._evaluate_for_side(board)

        key = _position_key(board)
        repetition_key = _repetition_key(board)
        self._pv[ply] = []
        if board.halfmove_clock >= 100 or self._path_counts.get(repetition_key, 0) >= 3 \
                or insufficient_material(board):
            return 0

        in_check = is_in_check(board)
        if depth <= 0:
            return self._quiescence(board, alpha, beta, ply, 0)

        original_alpha = alpha
        entry = self.transposition_table.get(key)
        tt_move = entry.best_move if entry else None
        if entry and entry.depth >= depth:
            tt_score = self._score_from_tt(entry.score, ply)
            if entry.flag == EXACT:
                self._pv[ply] = [entry.best_move] if entry.best_move else []
                return tt_score
            if entry.flag == LOWER_BOUND:
                alpha = max(alpha, tt_score)
            elif entry.flag == UPPER_BOUND:
                beta = min(beta, tt_score)
            if alpha >= beta:
                self._pv[ply] = [entry.best_move] if entry.best_move else []
                return tt_score

        moves = self._order_moves(board, generate_legal_moves(board), tt_move, ply)
        if not moves:
            self._pv[ply] = []
            return -MATE_SCORE + ply if in_check else 0

        best_score = -INFINITY
        best_move = None
        for move in moves:
            undo = board.make_move(move)
            child_key = _repetition_key(board)
            self._path_counts[child_key] = self._path_counts.get(child_key, 0) + 1
            try:
                score = -self._negamax(board, depth - 1, -beta, -alpha, ply + 1)
            finally:
                self._path_counts[child_key] -= 1
                if self._path_counts[child_key] == 0:
                    del self._path_counts[child_key]
                board.unmake_move(undo)

            if score > best_score:
                best_score = score
                best_move = move
                self._pv[ply] = [move] + self._pv[ply + 1][:]
            if score > alpha:
                alpha = score
            if alpha >= beta:
                if _captured_piece(board, move) is None and move.promotion is None:
                    self._record_quiet_cutoff(board, move, depth, ply)
                break

        flag = UPPER_BOUND if best_score <= original_alpha else LOWER_BOUND if best_score >= beta else EXACT
        if len(self.transposition_table) >= self.max_tt_entries:
            # A simple bounded policy keeps memory predictable; recent search
            # information is more useful than unbounded stale entries.
            self.transposition_table.clear()
        self.transposition_table[key] = TTEntry(
            depth, self._score_to_tt(best_score, ply), flag, best_move
        )
        return best_score

    def _quiescence(self, board: Board, alpha: int, beta: int,
                    ply: int, qply: int) -> int:
        self.qnodes += 1
        if (self.qnodes & 0xFF) == 0:
            self._check_time()
        if ply >= MAX_PLY - 1:
            return self._evaluate_for_side(board)

        repetition_key = _repetition_key(board)
        if board.halfmove_clock >= 100 or self._path_counts.get(repetition_key, 0) >= 3 \
                or insufficient_material(board):
            return 0

        in_check = is_in_check(board)
        moves = generate_legal_moves(board)
        if not moves:
            return -MATE_SCORE + ply if in_check else 0

        if not in_check:
            stand_pat = self._evaluate_for_side(board)
            if stand_pat >= beta:
                return stand_pat
            if stand_pat > alpha:
                alpha = stand_pat
            if qply >= QUIESCENCE_LIMIT:
                return alpha
            moves = [move for move in moves
                     if _captured_piece(board, move) is not None or move.promotion is not None]
        elif qply >= QUIESCENCE_LIMIT:
            # We cannot stand pat while in check. Search every legal evasion,
            # then use a static score as a hard safety boundary.
            best_evasion = -INFINITY
            for move in moves:
                undo = board.make_move(move)
                try:
                    score = -self._evaluate_for_side(board)
                    if score > best_evasion:
                        best_evasion = score
                finally:
                    board.unmake_move(undo)
                if best_evasion >= beta:
                    return best_evasion
            return max(alpha, best_evasion)

        if not moves:
            return alpha

        moves = self._order_moves(board, moves, None, ply)
        for move in moves:
            undo = board.make_move(move)
            child_key = _repetition_key(board)
            self._path_counts[child_key] = self._path_counts.get(child_key, 0) + 1
            try:
                score = -self._quiescence(board, -beta, -alpha, ply + 1, qply + 1)
            finally:
                self._path_counts[child_key] -= 1
                if self._path_counts[child_key] == 0:
                    del self._path_counts[child_key]
                board.unmake_move(undo)
            if score >= beta:
                return score
            if score > alpha:
                alpha = score
        return alpha

    def _order_moves(self, board: Board, moves: list[Move],
                     tt_move: Move | None, ply: int) -> list[Move]:
        color = board.side_to_move
        killers = self.killers.get(ply, [])

        def score(move: Move) -> int:
            if tt_move is not None and move == tt_move:
                return 2_000_000
            moving = board.squares[move.start]
            captured = _captured_piece(board, move)
            result = 0
            if captured is not None:
                result += 1_000_000 + PIECE_VALUES[captured.lower()] * 10
                if moving:
                    result -= PIECE_VALUES[moving.lower()]
            if move.promotion:
                result += 800_000 + PIECE_VALUES[move.promotion]
            if move in killers:
                result += 700_000 - killers.index(move) * 1_000
            if moving:
                result += self.history_heuristic.get((color, moving, move.end), 0)
            return result

        return sorted(moves, key=score, reverse=True)

    def _record_quiet_cutoff(self, board: Board, move: Move,
                             depth: int, ply: int) -> None:
        moving = board.squares[move.start]
        if moving is None:
            return
        killers = self.killers.setdefault(ply, [])
        if move not in killers:
            killers.insert(0, move)
            del killers[2:]
        key = (board.side_to_move, moving, move.end)
        self.history_heuristic[key] = min(
            100_000, self.history_heuristic.get(key, 0) + depth * depth
        )

    @staticmethod
    def _score_to_tt(score: int, ply: int) -> int:
        if score > MATE_THRESHOLD:
            return score + ply
        if score < -MATE_THRESHOLD:
            return score - ply
        return score

    @staticmethod
    def _score_from_tt(score: int, ply: int) -> int:
        if score > MATE_THRESHOLD:
            return score - ply
        if score < -MATE_THRESHOLD:
            return score + ply
        return score
