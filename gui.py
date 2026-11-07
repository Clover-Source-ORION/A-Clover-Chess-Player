"""Graphical CloverChess interface built with Python's standard-library Tkinter."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from board import Board, UNICODE_PIECES, index_to_square
from move import Move
from movegen import generate_legal_moves, is_in_check


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

        self.root.title("CloverChess — 0.2")
        self.root.configure(bg=self.BACKGROUND)
        self.root.minsize(930, 650)
        self.root.geometry("1050x720")

        self.status_var = tk.StringVar(value="White to move")
        self.fen_var = tk.StringVar(value=self.board.to_fen())
        self._build_layout()
        self._refresh()

    def _build_layout(self) -> None:
        outer = tk.Frame(self.root, bg=self.BACKGROUND, padx=18, pady=18)
        outer.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(outer, bg=self.BACKGROUND)
        header.pack(fill=tk.X, pady=(0, 14))
        tk.Label(header, text="CloverChess", bg=self.BACKGROUND, fg=self.TEXT,
                 font=("Segoe UI", 24, "bold")).pack(side=tk.LEFT)
        tk.Label(header, text="0.2  ·  0x88  ·  From scratch", bg=self.BACKGROUND,
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
        elif checked:
            side = "White" if self.board.side_to_move == "w" else "Black"
            self.status_var.set(f"{side} is in check")
        else:
            side = "White" if self.board.side_to_move == "w" else "Black"
            self.status_var.set(f"{side} to move")
        self.fen_var.set(self.board.to_fen())

    def _on_board_click(self, event: tk.Event) -> None:
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

    def _play_move(self, move: Move) -> None:
        undo = self.board.make_move(move)
        self.history.append((move, undo))
        side_label = "White" if undo.side_to_move == "w" else "Black"
        self.history_list.insert(tk.END, f"{self.board.fullmove_number - (1 if undo.side_to_move == 'b' else 0):>2}  {side_label:<5} {move.uci()}")
        self.history_list.yview_moveto(1.0)
        self.last_move = move
        self.selected_square = None
        self.selected_moves = []
        self._refresh()

    def _undo(self) -> None:
        if not self.history:
            self.status_var.set("Nothing to undo")
            return
        move, undo = self.history.pop()
        self.board.unmake_move(undo)
        self.history_list.delete(tk.END)
        self.last_move = self.history[-1][0] if self.history else None
        self._clear_selection()
        self._refresh()

    def _new_game(self) -> None:
        if self.history and not messagebox.askyesno("New game", "Discard the current game and start over?", parent=self.root):
            return
        self.board = Board.initial_position()
        self.history.clear()
        self.history_list.delete(0, tk.END)
        self.last_move = None
        self._clear_selection()
        self._refresh()

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
        self.history.clear()
        self.history_list.delete(0, tk.END)
        self.last_move = None
        self._clear_selection()
        self._refresh()


def run_gui(initial_fen: str | None = None) -> None:
    """Launch the graphical interface."""
    root = tk.Tk()
    CloverChessGUI(root, initial_fen=initial_fen)
    root.mainloop()
