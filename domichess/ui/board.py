# domichess/ui/board.py

import tkinter as tk
from tkinter import messagebox
import chess
import chess.svg
import io
from PIL import Image, ImageTk
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from domichess.ui.theme import Theme

class Board(tk.Frame):
    def __init__(self, parent, game, move_callback):
        super().__init__(parent)
        self.game = game
        self.move_callback = move_callback
        self.user_input_enabled = True
        self.board_theme = None
        self.piece_theme = None
        self.help_move_to_draw = None
        self.board_image = None # Keep a reference

        self.canvas = tk.Canvas(self, background=self.master.cget('bg'), highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.selected_square = None
        self.square_size = 1
        self.border_size = 0

        self.canvas.bind("<Button-1>", self.on_square_click)
        self.bind("<Configure>", self.on_resize)

    def apply_themes(self, board_theme, piece_theme):
        self.board_theme = board_theme
        self.piece_theme = piece_theme
        self.redraw_all()

    def set_user_input_enabled(self, enabled):
        self.user_input_enabled = enabled

    def on_resize(self, event):
        min_dim = min(event.width, event.height)
        self.border_size = min_dim // 20
        self.square_size = (min_dim - self.border_size * 2) // 8
        self.redraw_all()

    def redraw_all(self):
        self.canvas.delete("all")
        if self.square_size <= 0: return
        
        is_default_theme = self.board_theme and self.board_theme.name == "Default"

        if is_default_theme:
            self._draw_svg_board()
        else:
            border_color = self.board_theme.border_color if self.board_theme else Theme.border_color
            total_board_size = self.square_size * 8
            self.canvas.create_rectangle(0, 0, total_board_size + 2 * self.border_size, total_board_size + 2 * self.border_size, fill=border_color, outline="")
            self.draw_board()
            self.draw_coordinates()
            self.draw_pieces()
        
        if self.user_input_enabled and self.selected_square is not None:
            self.highlight_selected_square(self.selected_square)
            self.highlight_legal_moves(self.selected_square)
        
        if self.help_move_to_draw:
            self._draw_arrow(self.help_move_to_draw)

    def _draw_svg_board(self):
        board = self.game.get_board()
        last_move = board.peek() if board.move_stack else None
        check_square = board.king(board.turn) if board.is_check() else None
        
        svg_size = self.square_size * 8 + self.border_size * 2
        
        svg_code = chess.svg.board(
            board=board,
            size=svg_size,
            lastmove=last_move,
            check=check_square
        )
        
        try:
            drawing = svg2rlg(io.StringIO(svg_code))
            png_data = renderPM.drawToString(drawing, fmt="PNG", bg=None)
            pil_image = Image.open(io.BytesIO(png_data)).convert("RGBA")
            self.board_image = ImageTk.PhotoImage(pil_image)
            self.canvas.create_image(0, 0, image=self.board_image, anchor="nw")
        except Exception as e:
            print(f"Error generating SVG board: {e}")

    def on_square_click(self, event):
        self.help_move_to_draw = None
        if not self.user_input_enabled: return
        
        col = (event.x - self.border_size) // self.square_size
        row = (event.y - self.border_size) // self.square_size

        if not (0 <= col < 8 and 0 <= row < 8):
            self.selected_square = None; self.redraw_all(); return

        square_index = (7 - row) * 8 + col
        if self.selected_square is None:
            piece = self.game.get_board().piece_at(square_index)
            if piece and piece.color == self.game.get_board().turn:
                self.selected_square = square_index
        else:
            move_uci = f"{chess.SQUARE_NAMES[self.selected_square]}{chess.SQUARE_NAMES[square_index]}"
            if self.game.get_board().piece_at(self.selected_square).piece_type == chess.PAWN and (chess.square_rank(square_index) in [0, 7]):
                move_uci += 'q'
            self.move_callback(move_uci)
            self.selected_square = None
        self.redraw_all()

    def show_game_over_message(self):
        result = self.game.get_game_result()
        message = f"Game Over: {result}"
        messagebox.showinfo("Game Over", message)

    def draw_board(self):
        for row in range(8):
            for col in range(8):
                color_type = 'light' if (row + col) % 2 == 0 else 'dark'
                x1 = self.border_size + col * self.square_size; y1 = self.border_size + row * self.square_size
                
                if self.board_theme:
                    square_image = self.board_theme.get_square_image(color_type, self.square_size)
                    if square_image:
                        self.canvas.create_image(x1, y1, image=square_image, anchor="nw")
                        continue
                
                if self.board_theme:
                    color = self.board_theme.dark_square_color if color_type == 'dark' else self.board_theme.light_square_color
                else:
                    color = Theme.dark_square_color if color_type == 'dark' else Theme.light_square_color

                x2, y2 = x1 + self.square_size, y1 + self.square_size
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")

    def draw_coordinates(self):
        font_size = int(self.border_size * 0.5)
        if font_size < 8: return
        
        color = self.board_theme.coordinate_color if self.board_theme else "black"

        for i in range(8):
            x = self.border_size + i * self.square_size + self.square_size / 2
            y = self.border_size + i * self.square_size + self.square_size / 2
            self.canvas.create_text(x, self.border_size / 2, text=chr(ord('a') + i), fill=color, font=("Arial", font_size))
            self.canvas.create_text(x, self.border_size * 1.5 + 8 * self.square_size, text=chr(ord('a') + i), fill=color, font=("Arial", font_size))
            self.canvas.create_text(self.border_size / 2, y, text=str(8 - i), fill=color, font=("Arial", font_size))
            self.canvas.create_text(self.border_size * 1.5 + 8 * self.square_size, y, text=str(8 - i), fill=color, font=("Arial", font_size))

    def draw_pieces(self):
        board = self.game.get_board()
        for i in range(64):
            piece = board.piece_at(i)
            if piece:
                row, col = divmod(i, 8); row = 7 - row
                x = self.border_size + col * self.square_size + self.square_size / 2
                y = self.border_size + row * self.square_size + self.square_size / 2
                
                if self.piece_theme:
                    # Always pass the full chess.Piece object
                    piece_image = self.piece_theme.get_piece_image(piece, self.square_size)
                    if piece_image:
                        self.canvas.create_image(x, y, image=piece_image, tags="pieces")
                        continue
                
                # Fallback to unicode symbols is now handled inside get_piece_image if it returns None,
                # but we can add an explicit fallback here for total safety.
                # This part is now effectively dead code if piece_theme is always a valid Theme object.
                font_size = int(self.square_size * 0.6)
                if font_size < 1: continue
                symbols = {'P':'♙','R':'♖','N':'♘','B':'♗','Q':'♕','K':'♔','p':'♟','r':'♜','n':'♞','b':'♝','q':'♛','k':'♚'}
                self.canvas.create_text(x, y, text=symbols[piece.symbol()], font=("Arial", font_size), tags="pieces")

    def draw_help_arrow(self, move):
        self.help_move_to_draw = move; self.redraw_all()

    def _draw_arrow(self, move):
        from_row, from_col = divmod(move.from_square, 8); from_row = 7 - from_row
        to_row, to_col = divmod(move.to_square, 8); to_row = 7 - to_row
        x1 = self.border_size + from_col * self.square_size + self.square_size / 2
        y1 = self.border_size + from_row * self.square_size + self.square_size / 2
        x2 = self.border_size + to_col * self.square_size + self.square_size / 2
        y2 = self.border_size + to_row * self.square_size + self.square_size / 2
        self.canvas.create_line(x1, y1, x2, y2, arrow=tk.LAST, fill="orange", width=self.square_size * 0.1, tags="help_arrow")

    def highlight_selected_square(self, square_index):
        row, col = divmod(square_index, 8); row = 7 - row
        x1 = self.border_size + col * self.square_size; y1 = self.border_size + row * self.square_size
        x2, y2 = x1 + self.square_size, y1 + self.square_size
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="blue", width=3, tags="highlight")

    def highlight_legal_moves(self, from_square):
        board = self.game.get_board()
        for move in board.legal_moves:
            if move.from_square == from_square:
                to_square = move.to_square; row, col = divmod(to_square, 8); row = 7 - row
                x = self.border_size + col * self.square_size + self.square_size / 2
                y = self.border_size + row * self.square_size + self.square_size / 2
                radius = self.square_size * 0.1
                self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill="green", outline="", tags="highlight")
