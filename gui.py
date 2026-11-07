"""Graphical CloverChess interface built with Python's standard-library Tkinter."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from board import Board, UNICODE_PIECES, index_to_square
from move import Move
from movegen import generate_legal_moves, is_in_check
from engine import SearchResult, Searcher
from evaluation import insufficient_material


class CloverChessGUI:
    """A clickable chessboard UI that uses the CloverChess rules engine."""

    LIGHT_SQUARE = "#eee4d2"
    DARK_SQUARE = "#769656"
    SELECTED_SQUARE = "#f6f669"
    LAST_MOVE = "#cdd26a"
    LEGAL_DOT = "#405b33"
    BACKGROUND = "#202a36"
    PANEL = "#2b3847"
    TEXT = "#f1f5f9"
    MUTED = "#b8c3cf"
    SQUARE_SIZE = 72
    BOARD_SIZE = SQUARE_SIZE * 8

    def __init__(self, root: tk.Tk, initial_fen: str | None = None) -> None:
        self.root = root
        self.board = Board.from_fen(initial_fen) if initial_fen else Board.initial_position()
        self.history: list[tuple[Move, object]] = []
        self.selected_square: int | None = None
        self.selected_moves: list[Move] = []
        self.last_move: Move | None = None
        self.flipped = False
        self.mode_var = tk.StringVar(value="Play White (vs CloverChess)")
        self.strength_var = tk.StringVar(value="Standard")
        self.engine_info_var = tk.StringVar(value="Select a side and play against CloverChess.")
        self._position_revision = 0
        self._engine_results: queue.Queue = queue.Queue()
        self.searcher = Searcher()  # Reused between moves to retain the transposition table.
        self._engine_job_running = False
        self._engine_poll_after: str | None = None

        self.root.title("CloverChess — 0.3")
        self.root.configure(bg=self.BACKGROUND)
        self.root.minsize(930, 650)
        self.root.geometry("1050x720")

        self.status_var = tk.StringVar(value="White to move")
        self.fen_var = tk.StringVar(value=self.board.to_fen())
        self._build_layout()
        self._refresh()
        self._schedule_engine_move()

    def _build_layout(self) -> None:
        outer = tk.Frame(self.root, bg=self.BACKGROUND, padx=18, pady=18)
        outer.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(outer, bg=self.BACKGROUND)
        header.pack(fill=tk.X, pady=(0, 14))
        tk.Label(header, text="CloverChess", bg=self.BACKGROUND, fg=self.TEXT,
                 font=("Segoe UI", 24, "bold")).pack(side=tk.LEFT)
        tk.Label(header, text="0.3  ·  0x88  ·  Search engine", bg=self.BACKGROUND,
                 fg=self.MUTED, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(14, 0), pady=(10, 0))

        content = tk.Frame(outer, bg=self.BACKGROUND)
        content.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(content, width=self.BOARD_SIZE, height=self.BOARD_SIZE,
                                bg=self.BACKGROUND, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, anchor=tk.NW)
        self.canvas.bind("<Button-1>", self._on_board_click)

        panel = tk.Frame(content, bg=self.PANEL, padx=16, pady=14, width=330)
        panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(18, 0))
        panel.pack_propagate(False)

        tk.Label(panel, text="GAME STATUS", bg=self.PANEL, fg=self.MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        self.status_label = tk.Label(panel, textvariable=self.status_var, bg=self.PANEL,
                                     fg=self.TEXT, font=("Segoe UI", 16, "bold"),
                                     wraplength=290, justify=tk.LEFT)
        self.status_label.pack(anchor=tk.W, pady=(4, 14))

        button_row = tk.Frame(panel, bg=self.PANEL)
        button_row.pack(fill=tk.X, pady=(0, 14))
        self._make_button(button_row, "New game", self._new_game).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._make_button(button_row, "Undo", self._undo).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        self._make_button(button_row, "Flip", self._flip).pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(panel, text="OPPONENT", bg=self.PANEL, fg=self.MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.mode_box = ttk.Combobox(
            panel, textvariable=self.mode_var, state="readonly",
            values=("Play White (vs CloverChess)", "Play Black (vs CloverChess)", "Two players"),
        )
        self.mode_box.pack(fill=tk.X, pady=(0, 8))
        self.mode_box.bind("<<ComboboxSelected>>", self._on_mode_changed)

        tk.Label(panel, text="ENGINE STRENGTH", bg=self.PANEL, fg=self.MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.strength_box = ttk.Combobox(
            panel, textvariable=self.strength_var, state="readonly",
            values=("Quick", "Standard", "Strong"),
        )
        self.strength_box.pack(fill=tk.X, pady=(0, 5))
        self.strength_box.bind("<<ComboboxSelected>>", self._on_strength_changed)
        tk.Label(panel, textvariable=self.engine_info_var, bg=self.PANEL, fg=self.MUTED,
                 font=("Consolas", 8), wraplength=290, justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 12))

        tk.Label(panel, text="MOVE HISTORY", bg=self.PANEL, fg=self.MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        history_frame = tk.Frame(panel, bg=self.PANEL)
        history_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 14))
        self.history_list = tk.Listbox(
            history_frame, bg="#17212b", fg=self.TEXT, selectbackground="#496b8b",
            font=("Consolas", 11), relief=tk.FLAT, highlightthickness=0,
            activestyle="none",
        )
        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_list.yview)
        self.history_list.configure(yscrollcommand=scrollbar.set)
        self.history_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Label(panel, text="POSITION FEN", bg=self.PANEL, fg=self.MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        self.fen_entry = tk.Entry(panel, textvariable=self.fen_var, bg="#17212b", fg=self.TEXT,
                                  insertbackground=self.TEXT, relief=tk.FLAT,
                                  font=("Consolas", 8), width=40)
        self.fen_entry.pack(fill=tk.X, pady=(6, 7), ipady=6)
        fen_buttons = tk.Frame(panel, bg=self.PANEL)
        fen_buttons.pack(fill=tk.X)
        self._make_button(fen_buttons, "Load FEN", self._load_fen).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._make_button(fen_buttons, "Copy FEN", self._copy_fen).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

        tk.Label(panel, text="Click a piece, then its destination. Promotions ask for Q/R/B/N.",
                 bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 9),
                 wraplength=285, justify=tk.LEFT).pack(anchor=tk.W, pady=(14, 0))

    def _make_button(self, parent: tk.Widget, label: str, command) -> tk.Button:
        return tk.Button(
            parent, text=label, command=command, bg="#41566c", fg=self.TEXT,
            activebackground="#526d87", activeforeground=self.TEXT,
            relief=tk.FLAT, bd=0, padx=8, pady=8, cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        )

    def _square_from_canvas(self, x: int, y: int) -> int | None:
        file_view = x // self.SQUARE_SIZE
        rank_view = y // self.SQUARE_SIZE
        if not (0 <= file_view < 8 and 0 <= rank_view < 8):
            return None
        if self.flipped:
            file_index = 7 - file_view
            rank_index = rank_view
        else:
            file_index = file_view
            rank_index = 7 - rank_view
        return rank_index * 16 + file_index

    def _canvas_coords(self, square: int) -> tuple[int, int]:
        file_index = square & 7
        rank_index = square >> 4
        if self.flipped:
            return 7 - file_index, rank_index
        return file_index, 7 - rank_index

    def _draw_board(self) -> None:
        self.canvas.delete("all")
        legal_targets = {move.end for move in self.selected_moves}
        last_squares = set()
        if self.last_move is not None:
            last_squares = {self.last_move.start, self.last_move.end}

        for rank_view in range(8):
            for file_view in range(8):
                x1 = file_view * self.SQUARE_SIZE
                y1 = rank_view * self.SQUARE_SIZE
                x2, y2 = x1 + self.SQUARE_SIZE, y1 + self.SQUARE_SIZE
                if self.flipped:
                    file_index, rank_index = 7 - file_view, rank_view
                else:
                    file_index, rank_index = file_view, 7 - rank_view
                square = rank_index * 16 + file_index
                fill = self.LIGHT_SQUARE if (file_index + rank_index) % 2 == 0 else self.DARK_SQUARE
                if square in last_squares:
                    fill = self.LAST_MOVE
                if square == self.selected_square:
                    fill = self.SELECTED_SQUARE
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=fill)

                piece = self.board.squares[square]
                if piece is not None:
                    glyph = UNICODE_PIECES[piece]
                    font_family = "Segoe UI Symbol"
                    if piece.isupper():
                        # A subtle dark shadow keeps the white-outline symbols readable.
                        self.canvas.create_text((x1 + x2) / 2 + 1, (y1 + y2) / 2 + 2,
                                                text=glyph, fill="#263238",
                                                font=(font_family, 43, "bold"))
                        piece_color = "#ffffff"
                    else:
                        piece_color = "#18212b"
                    self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2,
                                            text=glyph, fill=piece_color,
                                            font=(font_family, 43, "bold"))

                if square in legal_targets:
                    center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
                    if piece is None:
                        radius = 9
                        self.canvas.create_oval(center_x - radius, center_y - radius,
                                                center_x + radius, center_y + radius,
                                                fill=self.LEGAL_DOT, outline="")
                    else:
                        self.canvas.create_oval(x1 + 5, y1 + 5, x2 - 5, y2 - 5,
                                                outline=self.LEGAL_DOT, width=4)

        # Small file/rank labels are included inside the board's outer edge.
        for view in range(8):
            if self.flipped:
                file_label = "hgfedcba"[view]
                rank_label = str(view + 1)
            else:
                file_label = "abcdefgh"[view]
                rank_label = str(8 - view)
            self.canvas.create_text(view * self.SQUARE_SIZE + 7, self.BOARD_SIZE - 7,
                                    text=file_label, fill="#34443a", anchor=tk.SW,
                                    font=("Segoe UI", 8, "bold"))
            self.canvas.create_text(4, view * self.SQUARE_SIZE + 7,
                                    text=rank_label, fill="#34443a", anchor=tk.NW,
                                    font=("Segoe UI", 8, "bold"))

    def _refresh(self) -> None:
        self._draw_board()
        legal_moves = generate_legal_moves(self.board)
        checked = is_in_check(self.board)
        if not legal_moves:
            if checked:
                winner = "Black" if self.board.side_to_move == "w" else "White"
                self.status_var.set(f"Checkmate — {winner} wins")
            else:
                self.status_var.set("Stalemate — draw")
        elif insufficient_material(self.board):
            self.status_var.set("Draw — insufficient material")
        elif self.board.halfmove_clock >= 100:
            self.status_var.set("Draw claim available — 50-move rule")
        elif checked:
            side = "White" if self.board.side_to_move == "w" else "Black"
            self.status_var.set(f"{side} is in check")
        else:
            side = "White" if self.board.side_to_move == "w" else "Black"
            self.status_var.set(f"{side} to move")
        self.fen_var.set(self.board.to_fen())

    def _on_board_click(self, event: tk.Event) -> None:
        if self._is_engine_turn() or self._engine_job_running:
            return
        square = self._square_from_canvas(event.x, event.y)
        if square is None:
            return
        piece = self.board.squares[square]
        side = self.board.side_to_move

        if self.selected_square is None:
            if piece is not None and ((piece.isupper() and side == "w") or (piece.islower() and side == "b")):
                self._select_square(square)
            return

        if square == self.selected_square:
            self._clear_selection()
            return

        candidates = [move for move in self.selected_moves if move.end == square]
        if candidates:
            chosen = candidates[0]
            if len(candidates) > 1 and all(move.promotion for move in candidates):
                choice = simpledialog.askstring(
                    "Pawn promotion", "Promote to queen, rook, bishop or knight? (q/r/b/n)",
                    initialvalue="q", parent=self.root,
                )
                if choice is None:
                    return
                promotion = choice.strip().lower()[:1]
                if promotion not in ("q", "r", "b", "n"):
                    messagebox.showwarning("Invalid promotion", "Choose q, r, b or n.", parent=self.root)
                    return
                chosen = next(move for move in candidates if move.promotion == promotion)
            self._play_move(chosen)
            return

        if piece is not None and ((piece.isupper() and side == "w") or (piece.islower() and side == "b")):
            self._select_square(square)
        else:
            self._clear_selection()

    def _select_square(self, square: int) -> None:
        self.selected_square = square
        self.selected_moves = [move for move in generate_legal_moves(self.board) if move.start == square]
        self._draw_board()

    def _clear_selection(self) -> None:
        self.selected_square = None
        self.selected_moves = []
        self._draw_board()

    def _play_move(self, move: Move, engine_result: SearchResult | None = None) -> None:
        undo = self.board.make_move(move)
        self.history.append((move, undo))
        self._position_revision += 1
        side_label = "White" if undo.side_to_move == "w" else "Black"
        self.history_list.insert(tk.END, f"{self.board.fullmove_number - (1 if undo.side_to_move == 'b' else 0):>2}  {side_label:<5} {move.uci()}")
        self.history_list.yview_moveto(1.0)
        self.last_move = move
        self.selected_square = None
        self.selected_moves = []
        self._refresh()
        if engine_result is not None:
            score = engine_result.score / 100.0
            pv = " ".join(engine_result.principal_variation[:6])
            self.engine_info_var.set(
                f"depth {engine_result.depth} · {engine_result.nodes:,} nodes · "
                f"{engine_result.nodes_per_second:,} n/s · eval {score:+.2f}\nPV: {pv}"
            )
        self._schedule_engine_move()

    def _undo(self) -> None:
        if not self.history:
            self.status_var.set("Nothing to undo")
            return
        undo_count = 1
        human_color = self._human_color()
        if human_color is not None and self.board.side_to_move == human_color and len(self.history) >= 2:
            undo_count = 2
        for _ in range(min(undo_count, len(self.history))):
            move, undo = self.history.pop()
            self.board.unmake_move(undo)
            self.history_list.delete(tk.END)
        self._position_revision += 1
        self.last_move = self.history[-1][0] if self.history else None
        self._clear_selection()
        self._refresh()
        self._schedule_engine_move()

    def _new_game(self) -> None:
        if self.history and not messagebox.askyesno("New game", "Discard the current game and start over?", parent=self.root):
            return
        self.board = Board.initial_position()
        self._position_revision += 1
        self.engine_info_var.set("New game. CloverChess is ready.")
        self.history.clear()
        self.history_list.delete(0, tk.END)
        self.last_move = None
        self._clear_selection()
        self._refresh()
        self._schedule_engine_move()

    def _flip(self) -> None:
        self.flipped = not self.flipped
        self._draw_board()

    def _copy_fen(self) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(self.board.to_fen())
        self.status_var.set("FEN copied to clipboard")

    def _load_fen(self) -> None:
        try:
            replacement = Board.from_fen(self.fen_var.get())
        except ValueError as exc:
            messagebox.showerror("Invalid FEN", str(exc), parent=self.root)
            return
        self.board = replacement
        self._position_revision += 1
        self.history.clear()
        self.history_list.delete(0, tk.END)
        self.last_move = None
        self._clear_selection()
        self._refresh()
        self._schedule_engine_move()

    def _engine_color(self) -> str | None:
        if self.mode_var.get() == "Play White (vs CloverChess)":
            return "b"
        if self.mode_var.get() == "Play Black (vs CloverChess)":
            return "w"
        return None

    def _human_color(self) -> str | None:
        engine_color = self._engine_color()
        if engine_color is None:
            return None
        return "b" if engine_color == "w" else "w"

    def _is_engine_turn(self) -> bool:
        engine_color = self._engine_color()
        return engine_color is not None and self.board.side_to_move == engine_color

    def _on_mode_changed(self, _event=None) -> None:
        self._position_revision += 1
        self.engine_info_var.set("Opponent mode changed.")
        self._clear_selection()
        self._refresh()
        self._schedule_engine_move()

    def _on_strength_changed(self, _event=None) -> None:
        self.engine_info_var.set(f"Engine strength: {self.strength_var.get()}.")

    def _schedule_engine_move(self) -> None:
        if self._engine_job_running or not self._is_engine_turn():
            return
        if not generate_legal_moves(self.board):
            return
        if insufficient_material(self.board) or self.board.halfmove_clock >= 100:
            self.status_var.set("Draw available under the current draw rules")
            return

        self._engine_job_running = True
        self.status_var.set("CloverChess is thinking…")
        self.engine_info_var.set("Searching candidate moves…")
        self._clear_selection()

        depth, time_limit = {
            "Quick": (3, 0.45),
            "Standard": (4, 1.35),
            "Strong": (5, 3.0),
        }.get(self.strength_var.get(), (4, 1.35))
        fen = self.board.to_fen()
        revision = self._position_revision
        worker = threading.Thread(
            target=self._engine_worker,
            args=(fen, revision, depth, time_limit),
            daemon=True,
        )
        worker.start()
        self._engine_poll_after = self.root.after(60, self._poll_engine_result)

    def _engine_worker(self, fen: str, revision: int, depth: int, time_limit: float) -> None:
        try:
            search_board = Board.from_fen(fen)
            result = self.searcher.search(search_board, max_depth=depth, time_limit=time_limit)
            self._engine_results.put((revision, fen, result, None))
        except Exception as exc:  # Keep worker failures visible instead of crashing Tk.
            self._engine_results.put((revision, fen, None, str(exc)))

    def _poll_engine_result(self) -> None:
        try:
            revision, fen, result, error = self._engine_results.get_nowait()
        except queue.Empty:
            self._engine_poll_after = self.root.after(60, self._poll_engine_result)
            return

        self._engine_job_running = False
        self._engine_poll_after = None
        if revision != self._position_revision or fen != self.board.to_fen():
            self._schedule_engine_move()
            return
        if error:
            self.engine_info_var.set(f"Search error: {error}")
            self._refresh()
            return
        if result is None or result.move is None:
            if insufficient_material(self.board):
                self.engine_info_var.set("CloverChess recognizes a draw by insufficient material.")
            elif self.board.halfmove_clock >= 100:
                self.engine_info_var.set("CloverChess accepts the 50-move draw claim.")
            self._refresh()
            return
        self._play_move(result.move, engine_result=result)


def run_gui(initial_fen: str | None = None) -> None:
    """Launch the graphical interface."""
    root = tk.Tk()
    CloverChessGUI(root, initial_fen=initial_fen)
    root.mainloop()
