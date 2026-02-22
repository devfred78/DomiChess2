# domichess/ui/main_window.py

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import chess
import chess.engine
from pathlib import Path
import threading
import random
import importlib.metadata
import sys
import textwrap
import domichess

from domichess.core.game import Game
from domichess.ui.board import Board
from domichess.ui.player_panel import PlayerPanel
from domichess.ui.theme import Theme

# --- Path setup ---
if getattr(sys, 'frozen', False):
    APP_ROOT = Path(sys.executable).parent
    SOURCE_ROOT = Path(sys._MEIPASS)
else:
    APP_ROOT = Path(__file__).resolve().parent.parent.parent
    SOURCE_ROOT = APP_ROOT

ICONS_DIR = SOURCE_ROOT / "domichess" / "icons"
THEME_SEARCH_PATHS = [APP_ROOT / "themes", SOURCE_ROOT / "domichess" / "themes"]
ENGINE_SEARCH_PATHS = [APP_ROOT / "engines", SOURCE_ROOT / "domichess" / "engines"]

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        
        print("--- Initializing DomiChess2 ---")
        self.game = Game()
        self.engine_paths = self.load_engine_paths()
        self.board_themes = self._load_themes_from("boards", "Board")
        self.piece_themes = self._load_themes_from("pieces", "Piece")
        self.active_engines = {}
        self.game_running = False
        self._theme_update_lock = False
        self.current_player_photo_image = None
        self.blank_image = tk.PhotoImage(width=64, height=64)

        self.help_engine_name = None
        if self.engine_paths:
            engine_names = self.engine_paths.keys()
            self.help_engine_name = next((name for name in engine_names if "madchess" in name.lower()), None)
            if not self.help_engine_name:
                self.help_engine_name = random.choice(list(engine_names))
        
        self.set_title_and_icon()
        print("-----------------------------")

        # --- Layout ---
        self.top_theme_bar = tk.LabelFrame(self, text="Themes", labelanchor="nw", padx=10, pady=5)
        self.top_theme_bar.pack(side=tk.TOP, fill="x", padx=10, pady=(10, 0))
        self.main_content_frame = tk.Frame(self)
        self.main_content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.left_panel = tk.Frame(self.main_content_frame)
        self.left_panel.pack(side=tk.LEFT, fill="y", padx=(0, 10))
        
        cburnett_theme_name = "John Pablok Cburnett set (with shadow)"
        startup_board_theme = self._get_first_non_default(self.board_themes) or "Default"
        startup_piece_theme = cburnett_theme_name if cburnett_theme_name in self.piece_themes else (self._get_first_non_default(self.piece_themes) or "Default")
        
        self._last_board_theme = startup_board_theme
        self._last_piece_theme = startup_piece_theme
        self._create_theme_selectors(self.top_theme_bar, startup_board_theme, startup_piece_theme)

        # --- Current Player Display ---
        self.current_player_frame = tk.LabelFrame(self.left_panel, text="Current Player")
        self.current_player_frame.pack(side=tk.TOP, pady=(0, 10), fill="x")
        self.current_player_image_label = tk.Label(self.current_player_frame, image=self.blank_image)
        self.current_player_image_label.pack(pady=10)

        # --- Player Panels ---
        self.white_display_piece = chess.Piece(random.choice([chess.KNIGHT, chess.QUEEN, chess.ROOK, chess.BISHOP]), chess.WHITE)
        self.black_display_piece = chess.Piece(random.choice([chess.KNIGHT, chess.QUEEN, chess.ROOK, chess.BISHOP]), chess.BLACK)
        
        self.white_player_panel = PlayerPanel(self.left_panel, "White", self.engine_paths, self.white_display_piece)
        self.white_player_panel.pack(side=tk.TOP, fill="x", pady=5)
        self.black_player_panel = PlayerPanel(self.left_panel, "Black", self.engine_paths, self.black_display_piece)
        self.black_player_panel.pack(side=tk.TOP, fill="x", pady=5)
        self.white_player_panel.set_callback(self.on_player_change)
        self.black_player_panel.set_callback(self.on_player_change)

        # --- Game Controls ---
        controls_frame = tk.Frame(self.left_panel)
        controls_frame.pack(side=tk.TOP, pady=20)

        self.start_button = tk.Button(controls_frame, text="Start Game", command=self.start_game, background="green", foreground="white")
        self.start_button.pack(side=tk.LEFT, padx=2)
        
        if self.engine_paths:
            self.help_button = tk.Button(controls_frame, text="Help", command=self.on_help_request, background="orange", foreground="black")
            self.help_button.pack(side=tk.LEFT, padx=2)
        
        self.new_game_button = tk.Button(controls_frame, text="New Game", command=self.confirm_new_game, background="red", foreground="white")
        self.new_game_button.pack(side=tk.LEFT, padx=2)

        self.board = Board(self.main_content_frame, self.game, self.on_human_move)
        self.board.pack(side=tk.LEFT, fill="both", expand=True)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.after(20, self.on_theme_change)
        self.reset_ui_to_setup()
        
        self.update_idletasks()
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        self.geometry(f"{width}x{height}")
        self.minsize(width, height)

    def set_title_and_icon(self):
        name = "DomiChess2"
        version = ""
        try:
            dist_name = 'DomiChess2'
            version = importlib.metadata.version(dist_name)
            name = importlib.metadata.metadata(dist_name)['Name']
        except importlib.metadata.PackageNotFoundError:
            version = domichess.__version__
        
        title = f"{name} {version}"
        if self.help_engine_name:
            title += f" (powered by {self.help_engine_name})"
        self.title(title)

        icon_path = ICONS_DIR / "chess_64px.ico"
        if icon_path.is_file():
            try: self.iconbitmap(icon_path)
            except: print(f"Could not load icon from {icon_path}.")
        else: print(f"Icon file not found at {icon_path}")

    def _update_current_player_display(self):
        if not self.game_running:
            self.current_player_image_label.config(image=self.blank_image)
            self.current_player_photo_image = None
            return

        current_color = self.game.get_board().turn
        display_piece = self.white_display_piece if current_color == chess.WHITE else self.black_display_piece
        
        piece_theme_name = self.piece_theme_var.get()
        piece_theme = self.piece_themes.get(piece_theme_name)

        if piece_theme:
            self.current_player_photo_image = piece_theme.get_piece_image(display_piece, 64)
            self.current_player_image_label.config(image=self.current_player_photo_image)
        else:
            self.current_player_image_label.config(image=self.blank_image)

    def set_ui_state(self, is_game_running):
        self.game_running = is_game_running
        state = tk.DISABLED if is_game_running else tk.NORMAL
        
        for panel in [self.white_player_panel, self.black_player_panel]:
            self._set_interactive_widgets_state(panel, state)

        self.start_button.config(state=tk.DISABLED if is_game_running else tk.NORMAL)
        self.new_game_button.config(state=tk.NORMAL if is_game_running else tk.DISABLED)
        if hasattr(self, 'help_button'):
            self.help_button.config(state=tk.NORMAL if is_game_running else tk.DISABLED)
        
        self._update_current_player_display()

    def on_theme_change(self, *args):
        if self._theme_update_lock: return
        self._theme_update_lock = True

        current_board = self.board_theme_var.get()
        current_pieces = self.piece_theme_var.get()
        board_changed = current_board != self._last_board_theme
        pieces_changed = current_pieces != self._last_piece_theme

        if (board_changed and current_board == "Default") or (pieces_changed and current_pieces == "Default"):
            self.board_theme_var.set("Default"); self.piece_theme_var.set("Default")
        elif board_changed and self._last_board_theme == "Default":
            if current_pieces == "Default":
                first_other = self._get_first_non_default(self.piece_themes)
                if first_other: self.piece_theme_var.set(first_other)
        elif pieces_changed and self._last_piece_theme == "Default":
            if current_board == "Default":
                first_other = self._get_first_non_default(self.board_themes)
                if first_other: self.board_theme_var.set(first_other)

        final_board_name = self.board_theme_var.get()
        final_pieces_name = self.piece_theme_var.get()
        board_theme = self.board_themes.get(final_board_name)
        piece_theme = self.piece_themes.get(final_pieces_name)

        self.board.apply_themes(board_theme, piece_theme)
        self.white_player_panel.update_piece_display(piece_theme)
        self.black_player_panel.update_piece_display(piece_theme)
        self._update_current_player_display()

        self._last_board_theme = final_board_name
        self._last_piece_theme = final_pieces_name
        
        self._theme_update_lock = False

    def game_loop(self):
        if not self.game_running or self.game.is_game_over():
            if self.game.is_game_over():
                self.board.show_game_over_message()
                self.reset_ui_to_setup()
            return
        
        self._update_current_player_display()
        
        color = "White" if self.game.get_board().turn == chess.WHITE else "Black"
        if color in self.active_engines:
            self.board.set_user_input_enabled(False)
            self.make_engine_move(color)
        else:
            self.board.set_user_input_enabled(True)
        
        self.after(100, self.game_loop)

    def make_engine_move(self, color):
        if not self.game_running or color not in self.active_engines: return
        if hasattr(self, f'_engine_move_in_progress_{color}') and getattr(self, f'_engine_move_in_progress_{color}'): return
        setattr(self, f'_engine_move_in_progress_{color}', True)
        def think_and_move():
            try:
                engine_info = self.active_engines[color]
                result = engine_info["process"].play(self.game.get_board(), chess.engine.Limit(time=engine_info["time"]))
                def apply_move():
                    if self.game_running:
                        self.game.move(result.move.uci())
                        self.board.redraw_all()
                    setattr(self, f'_engine_move_in_progress_{color}', False)
                self.after(0, apply_move)
            except Exception as e:
                print(f"Engine error for {color}: {e}"); setattr(self, f'_engine_move_in_progress_{color}', False)
        threading.Thread(target=think_and_move, daemon=True).start()

    def on_player_change(self, event=None):
        if self.game_running:
            if messagebox.askyesno("Restart Game", "Changing player type requires a new game. Restart?"):
                self.reset_ui_to_setup()

    def on_human_move(self, move):
        if self.game_running:
            self.game.move(move)
            self.board.redraw_all()

    def _get_first_non_default(self, themes_dict):
        for name in themes_dict.keys():
            if name != "Default":
                return name
        return None

    def _create_user_dir_if_needed(self, base_path, sub_dir, resource_type):
        if getattr(sys, 'frozen', False):
            user_dir = base_path / sub_dir
            if not user_dir.is_dir():
                try:
                    user_dir.mkdir(parents=True, exist_ok=True)
                    readme_path = user_dir / f"PUT_YOUR_{resource_type.upper()}_HERE.txt"
                    if resource_type == "Board": readme_text = textwrap.dedent("""...""").strip()
                    elif resource_type == "Piece": readme_text = textwrap.dedent("""...""").strip()
                    else: readme_text = textwrap.dedent("""...""").strip()
                    readme_path.write_text(readme_text, encoding="utf-8")
                except Exception as e:
                    print(f"  Warning: Could not create user {resource_type} directory or helper file: {e}")

    def _load_themes_from(self, sub_dir, theme_type):
        self._create_user_dir_if_needed(APP_ROOT / "themes", sub_dir, theme_type)
        themes = {"Default": Theme("Default")}
        print(f"--- Searching for {theme_type} themes ---")
        for base_path in THEME_SEARCH_PATHS:
            path = base_path / sub_dir
            if path.is_dir():
                print(f"Searching in: {path}")
                for theme_dir in path.iterdir():
                    if theme_dir.is_dir():
                        name_file = theme_dir / "name.txt"; theme_name = theme_dir.name
                        if name_file.is_file():
                            try: theme_name = name_file.read_text(encoding="utf-8").strip()
                            except Exception as e: print(f"Could not read theme name from {name_file}: {e}")
                        if theme_name not in themes:
                            print(f"  Found theme: '{theme_name}'"); themes[theme_name] = Theme(theme_name, theme_dir)
                        else:
                            print(f"  Skipping duplicate theme: '{theme_name}'")
        print(f"Detected {theme_type} themes: {list(themes.keys())}")
        return themes

    def load_engine_paths(self):
        self._create_user_dir_if_needed(APP_ROOT, "engines", "engines")
        engines = {}
        print("--- Searching for engines ---")
        for path in ENGINE_SEARCH_PATHS:
            if path.is_dir():
                print(f"Searching in: {path}")
                for exe_path in path.rglob("*.exe"):
                    try:
                        engine = chess.engine.SimpleEngine.popen_uci(str(exe_path)); engine_name = engine.id['name']; engine.quit()
                        if engine_name not in engines:
                            print(f"  Found engine: {engine_name} (from {exe_path.name})"); engines[engine_name] = str(exe_path)
                        else:
                            print(f"  Skipping duplicate engine: {engine_name}")
                    except Exception as e:
                        print(f"  Could not load engine {exe_path.name}: {e}")
        print(f"Detected engines: {list(engines.keys())}")
        return engines

    def _set_interactive_widgets_state(self, parent_widget, state):
        for child in parent_widget.winfo_children():
            if isinstance(child, (tk.Button, tk.Entry, tk.Spinbox, tk.Scale, tk.OptionMenu, ttk.Notebook)):
                try: child.configure(state=state)
                except tk.TclError: pass
            self._set_interactive_widgets_state(child, state)

    def reset_ui_to_setup(self):
        self.quit_all_engines(); self.game.reset(); self.board.redraw_all(); self.set_ui_state(is_game_running=False)

    def start_game(self):
        white_config = self.white_player_panel.get_player_config(); black_config = self.black_player_panel.get_player_config()
        self.set_ui_state(is_game_running=True); self.quit_all_engines(); self.game.reset()
        self.active_engines["White"] = self._configure_engine(white_config)
        self.active_engines["Black"] = self._configure_engine(black_config)
        self.active_engines = {k: v for k, v in self.active_engines.items() if v}
        self.board.selected_square = None; self.board.redraw_all(); self.after(100, self.game_loop)

    def _configure_engine(self, config):
        if config["type"] != "cpu": return None
        try:
            engine_process = chess.engine.SimpleEngine.popen_uci(self.engine_paths[config["engine"]])
            if "elo" in config and "UCI_Elo" in engine_process.options:
                engine_process.configure({"UCI_LimitStrength": True, "UCI_Elo": config["elo"]})
            return {"process": engine_process, "time": config["time"]}
        except Exception as e:
            print(f"Failed to start or configure engine {config['engine']}: {e}"); return None

    def confirm_new_game(self):
        if messagebox.askyesno("New Game", "Are you sure? This will stop the current game and return to the setup screen."):
            self.reset_ui_to_setup()

    def quit_all_engines(self):
        for engine_info in self.active_engines.values():
            try: engine_info["process"].quit()
            except: pass
        self.active_engines.clear()

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"): self.quit_all_engines(); self.destroy()
    
    def _create_theme_selectors(self, parent, startup_board, startup_pieces):
        board_frame = tk.Frame(parent); board_frame.pack(side=tk.LEFT, padx=20, pady=5)
        tk.Label(board_frame, text="Board:").pack(side=tk.LEFT, padx=(0, 5))
        self.board_theme_var = tk.StringVar(value=startup_board)
        self.board_theme_menu = tk.OptionMenu(board_frame, self.board_theme_var, *self.board_themes.keys())
        self.board_theme_menu.pack(side=tk.LEFT)
        self.board_theme_var.trace_add("write", self.on_theme_change)
        
        piece_frame = tk.Frame(parent); piece_frame.pack(side=tk.RIGHT, padx=20, pady=5)
        tk.Label(piece_frame, text="Pieces:").pack(side=tk.LEFT, padx=(0, 5))
        self.piece_theme_var = tk.StringVar(value=startup_pieces)
        self.piece_theme_menu = tk.OptionMenu(piece_frame, self.piece_theme_var, *self.piece_themes.keys())
        self.piece_theme_menu.pack(side=tk.LEFT)
        self.piece_theme_var.trace_add("write", self.on_theme_change)

    def on_help_request(self):
        if not self.game_running or not self.help_engine_name: return
        self.help_button.config(state=tk.DISABLED)
        def get_best_move():
            try:
                engine = chess.engine.SimpleEngine.popen_uci(self.engine_paths[self.help_engine_name])
                result = engine.play(self.game.get_board(), chess.engine.Limit(time=0.5)); engine.quit()
                self.after(0, lambda: (self.board.draw_help_arrow(result.move), self.help_button.config(state=tk.NORMAL)))
            except Exception as e: print(f"Help engine error: {e}"); self.help_button.config(state=tk.NORMAL)
        threading.Thread(target=get_best_move, daemon=True).start()
