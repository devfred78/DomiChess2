# domichess/ui/main_window.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import chess
import chess.engine
import chess.pgn
from pathlib import Path
import threading
import random
import importlib.metadata
import sys
import textwrap
from datetime import datetime
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
    # In dev mode, we need to manually add the parallel directory to the path
    MULTIPLAYER_PATH = APP_ROOT.parent / "multiplayer"
    if MULTIPLAYER_PATH.exists():
        sys.path.insert(0, str(MULTIPLAYER_PATH))

try:
    from multiplayer.client import GameClient, RemoteGame
    from multiplayer.server import GameServer
    from multiplayer.game import Player
    MULTIPLAYER_AVAILABLE = True
except ImportError:
    MULTIPLAYER_AVAILABLE = False


ICONS_DIR = SOURCE_ROOT / "domichess" / "icons"
THEME_SEARCH_PATHS = [APP_ROOT / "themes", SOURCE_ROOT / "domichess" / "themes"]
ENGINE_SEARCH_PATHS = [APP_ROOT / "engines", SOURCE_ROOT / "domichess" / "engines"]

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.game = Game()
        self.active_engines = {}
        self.game_running = False
        self.is_handling_game_end = False
        self._theme_update_lock = False
        self.current_player_photo_image = None
        self.blank_image = tk.PhotoImage(width=64, height=64)
        self.white_player_config = None
        self.black_player_config = None
        self.game_server = None
        self.remote_game = None
        self.is_remote_game = False
        self.local_player_color = None

        # --- Layout ---
        self.top_theme_bar = tk.LabelFrame(self, text="Themes", labelanchor="nw", padx=10, pady=5)
        self.top_theme_bar.pack(side=tk.TOP, fill="x", padx=10, pady=(10, 0))
        self.main_content_frame = tk.Frame(self)
        self.main_content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.left_panel = tk.Frame(self.main_content_frame)
        self.left_panel.pack(side=tk.LEFT, fill="y", padx=(0, 10))
        
        self.current_player_frame = tk.LabelFrame(self.left_panel, text="Current Player")
        self.current_player_frame.pack(side=tk.TOP, pady=(0, 10), fill="x")
        self.current_player_image_label = tk.Label(self.current_player_frame, image=self.blank_image)
        self.current_player_image_label.pack(pady=10)

        self.white_display_piece = chess.Piece(random.choice([chess.KNIGHT, chess.QUEEN, chess.ROOK, chess.BISHOP]), chess.WHITE)
        self.black_display_piece = chess.Piece(random.choice([chess.KNIGHT, chess.QUEEN, chess.ROOK, chess.BISHOP]), chess.BLACK)
        
        self.white_player_panel = PlayerPanel(self, "White", {}, self.white_display_piece)
        self.white_player_panel.pack(side=tk.TOP, fill="x", pady=5)
        self.black_player_panel = PlayerPanel(self, "Black", {}, self.black_display_piece)
        self.black_player_panel.pack(side=tk.TOP, fill="x", pady=5)
        self.white_player_panel.set_callback(self.on_player_change)
        self.black_player_panel.set_callback(self.on_player_change)

        controls_frame = tk.Frame(self.left_panel)
        controls_frame.pack(side=tk.TOP, pady=20)

        self.start_button = tk.Button(controls_frame, text="Start Game", command=self.start_game, background="green", foreground="white")
        self.start_button.pack(side=tk.LEFT, padx=2)
        
        self.help_button = tk.Button(controls_frame, text="Help", command=self.on_help_request, background="orange", foreground="black")
        self.help_button.pack(side=tk.LEFT, padx=2)
        
        self.new_game_button = tk.Button(controls_frame, text="New Game", command=self.confirm_new_game, background="red", foreground="white")
        self.new_game_button.pack(side=tk.LEFT, padx=2)
        
        self.save_pgn_button = tk.Button(controls_frame, text="Save PGN", command=self.prompt_for_pgn_save, background="blue", foreground="white")
        self.save_pgn_button.pack(side=tk.LEFT, padx=2)

        if MULTIPLAYER_AVAILABLE:
            self.host_button = tk.Button(self.left_panel, text="Host Multiplayer Game", command=self.prompt_for_host_options)
            self.host_button.pack(side=tk.TOP, pady=(10,0), fill="x")

        log_frame = tk.LabelFrame(self.left_panel, text="Game Log")
        log_frame.pack(side=tk.TOP, fill="x", pady=(10, 0), expand=True)

        self.log_text = tk.Text(log_frame, height=10, wrap="word", state="disabled", font=("Consolas", 9))
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.log_text.pack(side=tk.LEFT, fill="both", expand=True)
        
        self.log_message("Welcome to DomiChess2!")
        if not MULTIPLAYER_AVAILABLE:
            self.log_message("Multiplayer library not found.")

        self.engine_paths = self.load_engine_paths()
        self.board_themes = self._load_themes_from("boards", "Board")
        self.piece_themes = self._load_themes_from("pieces", "Piece")
        
        self.white_player_panel.update_engine_list(self.engine_paths)
        self.black_player_panel.update_engine_list(self.engine_paths)
        if not self.engine_paths:
            self.help_button.pack_forget()

        self.help_engine_name = None
        if self.engine_paths:
            engine_names = self.engine_paths.keys()
            self.help_engine_name = next((name for name in engine_names if "madchess" in name.lower()), None)
            if not self.help_engine_name:
                self.help_engine_name = random.choice(list(engine_names))
            self.log_message(f"Help engine: {self.help_engine_name}")

        self.set_title_and_icon()
        
        cburnett_theme_name = "John Pablok Cburnett set (with shadow)"
        startup_board_theme = self._get_first_non_default(self.board_themes) or "Default"
        startup_piece_theme = cburnett_theme_name if cburnett_theme_name in self.piece_themes else (self._get_first_non_default(self.piece_themes) or "Default")
        
        self._last_board_theme = startup_board_theme
        self._last_piece_theme = startup_piece_theme
        self._create_theme_selectors(self.top_theme_bar, startup_board_theme, startup_piece_theme)

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

    def prompt_for_host_options(self):
        dialog = tk.Toplevel(self)
        dialog.title("Host Game Options")

        secure_var = tk.BooleanVar()
        password_var = tk.StringVar()
        tls_var = tk.BooleanVar()
        port_var = tk.IntVar(value=65432)

        def toggle_password_entry():
            state = tk.NORMAL if secure_var.get() else tk.DISABLED
            password_entry.config(state=state)

        tk.Checkbutton(dialog, text="Secure with password", variable=secure_var, command=toggle_password_entry).grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        
        tk.Label(dialog, text="Password:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        password_entry = tk.Entry(dialog, textvariable=password_var, show="*", state=tk.DISABLED)
        password_entry.grid(row=1, column=1, padx=10, pady=5)

        tk.Checkbutton(dialog, text="Use TLS encryption", variable=tls_var).grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        
        tk.Label(dialog, text="Port:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        tk.Entry(dialog, textvariable=port_var, width=10).grid(row=3, column=1, padx=10, pady=5, sticky="w")

        def on_ok():
            password = password_var.get() if secure_var.get() else None
            use_tls = tls_var.get()
            try:
                port = port_var.get()
            except tk.TclError:
                messagebox.showerror("Invalid Port", "Port must be a number.")
                return
            
            dialog.destroy()
            self.host_game(password=password, use_tls=use_tls, port=port)

        ok_button = tk.Button(dialog, text="Host", command=on_ok)
        ok_button.grid(row=4, column=0, columnspan=2, pady=10)
        
        dialog.transient(self)
        dialog.grab_set()
        self.wait_window(dialog)

    def host_game(self, password=None, use_tls=False, port=65432):
        if not MULTIPLAYER_AVAILABLE:
            self.log_message("Cannot host: Multiplayer library not available.")
            return
        if self.game_server and self.game_server._server_process.is_alive():
            self.log_message("Server is already running.")
            return
        
        try:
            self.game_server = GameServer(port=port, password=password, use_tls=use_tls)
            self.game_server.start()
            
            log_msg = f"Multiplayer server started on port {port}."
            if password:
                log_msg = "Secure " + log_msg
            if use_tls:
                log_msg += " (TLS enabled)"
            self.log_message(log_msg)
            self.host_button.config(text="Stop Server", command=self.stop_game_server)
        except (PermissionError, OSError) as e:
            self.log_message(f"Failed to start server: {e}")
            messagebox.showerror("Server Error", 
                f"Could not start the server on port {port}.\n\n"
                "Possible reasons:\n"
                "- The port is already in use.\n"
                "- Windows Firewall is blocking the connection.\n"
                "- You need administrator privileges.\n\n"
                "Try changing the port number or checking your firewall settings."
            )
            self.game_server = None

    def stop_game_server(self, confirm=True):
        if self.game_server and self.game_server._server_process.is_alive():
            do_stop = not confirm or messagebox.askyesno("Stop Server", "Are you sure you want to stop the server? This will disconnect all players.")
            if do_stop:
                self.game_server.stop()
                self.game_server = None
                self.log_message("Server stopped by user.")
                self.host_button.config(text="Host Multiplayer Game", command=self.prompt_for_host_options)

    def log_message(self, message, clear=False):
        self.log_text.config(state="normal")
        if clear:
            self.log_text.delete("1.0", tk.END)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.config(state="disabled")
        self.log_text.see(tk.END)

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
            except: self.log_message(f"Warning: Could not load icon.")
        else: self.log_message(f"Warning: Icon file not found.")

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
        self.save_pgn_button.config(state=tk.NORMAL if is_game_running else tk.DISABLED)
        if hasattr(self, 'help_button'):
            self.help_button.config(state=tk.NORMAL if is_game_running else tk.DISABLED)
        if hasattr(self, 'host_button'):
            is_hosting = self.game_server and self.game_server._server_process.is_alive()
            if not is_hosting:
                self.host_button.config(text="Host Multiplayer Game", command=self.prompt_for_host_options)
        
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
        if not self.game_running:
            return
        
        if self.game.is_game_over():
            if not self.is_remote_game:
                result = self.game.get_game_result()
                self.log_message(f"Game over: {result}")
                self.board.show_game_over_message()
                self.set_ui_state(is_game_running=True)
            return
        
        self._update_current_player_display()
        
        if self.is_remote_game:
            self.fetch_remote_state()

        current_turn_color = self.game.get_board().turn
        is_local_turn = (self.local_player_color is None) or (current_turn_color == self.local_player_color)

        if not self.is_remote_game or is_local_turn:
            color = "White" if current_turn_color == chess.WHITE else "Black"
            if color in self.active_engines:
                self.board.set_user_input_enabled(False)
                self.make_engine_move(color)
            else:
                self.board.set_user_input_enabled(True)
        else: # Remote game and it's the opponent's turn
            self.board.set_user_input_enabled(False)
        
        self.after(1000, self.game_loop)

    def fetch_remote_state(self):
        if not self.is_remote_game or not self.remote_game:
            return

        def fetch_thread_func():
            try:
                state = self.remote_game.state
                if state['status'] == 'finished':
                    self.after(0, self.handle_remote_game_end)
                    return

                if 'custom' in state and 'fen' in state['custom']:
                    current_fen = self.game.get_board().fen()
                    if state['custom']['fen'] != current_fen:
                        self.after(0, self._apply_remote_fen, state['custom']['fen'])
            except Exception:
                self.after(0, self.handle_remote_game_end)

        threading.Thread(target=fetch_thread_func, daemon=True).start()

    def handle_remote_game_end(self):
        if self.is_handling_game_end:
            return
        self.is_handling_game_end = True
        self.log_message("Opponent has left the game.")
        messagebox.showinfo("Game Over", "Your opponent has disconnected.")
        self.reset_ui_to_setup()

    def _apply_remote_fen(self, fen):
        board = self.game.get_board()
        
        found_move = None
        for move in board.legal_moves:
            temp_board = board.copy()
            temp_board.push(move)
            if temp_board.fen() == fen:
                found_move = move
                break

        if found_move:
            san = board.san(found_move)
            
            move_num_str = ""
            if board.turn == chess.WHITE:
                move_num_str = f"{board.fullmove_number}."
            else:
                move_num_str = f"{board.fullmove_number}. ..."

            self.game.move(found_move.uci())
            self.log_message(f"{move_num_str} {san}")
        else:
            self.game.get_board().set_fen(fen)
            self.log_message("Board updated from remote (full sync).")

        self.board.redraw_all()

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
                        self.on_human_move(result.move.uci())
                    setattr(self, f'_engine_move_in_progress_{color}', False)
                self.after(0, apply_move)
            except Exception as e:
                self.log_message(f"Engine error for {color}: {e}"); setattr(self, f'_engine_move_in_progress_{color}', False)
        threading.Thread(target=think_and_move, daemon=True).start()

    def on_player_change(self, event=None):
        if self.game_running:
            if messagebox.askyesno("Restart Game", "Changing player type requires a new game. Restart?"):
                self.reset_ui_to_setup()

    def on_human_move(self, move_uci):
        if self.game_running:
            try:
                move = chess.Move.from_uci(move_uci)
                san = self.game.get_board().san(move)
                
                move_num_str = ""
                if self.game.get_board().turn == chess.WHITE:
                    move_num_str = f"{self.game.get_board().fullmove_number}."

                if self.game.move(move_uci):
                    if self.game.get_board().turn == chess.WHITE:
                        move_num_str = f"{self.game.get_board().fullmove_number - 1}. ..."

                    self.log_message(f"{move_num_str} {san}")
                    self.board.redraw_all()

                    if self.is_remote_game and self.remote_game:
                        self.send_remote_state()
            except Exception as e:
                self.log_message(f"Error on move: {e}")

    def send_remote_state(self):
        if not self.is_remote_game or not self.remote_game:
            return
        
        new_fen = self.game.get_board().fen()
        
        def send_thread_func():
            try:
                self.remote_game.set_state({'fen': new_fen})
                self.after(0, self.log_message, "Sent new board state to remote.")
            except Exception as e:
                self.after(0, self.log_message, f"Error sending remote state: {e}")

        threading.Thread(target=send_thread_func, daemon=True).start()

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
                except Exception as e:
                    self.log_message(f"Warning: Could not create user {resource_type} directory.")

    def _load_themes_from(self, sub_dir, theme_type):
        self._create_user_dir_if_needed(APP_ROOT / "themes", sub_dir, theme_type)
        themes = {"Default": Theme("Default")}
        self.log_message(f"Searching for {theme_type} themes...")
        for base_path in THEME_SEARCH_PATHS:
            path = base_path / sub_dir
            if path.is_dir():
                for theme_dir in path.iterdir():
                    if theme_dir.is_dir():
                        name_file = theme_dir / "name.txt"; theme_name = theme_dir.name
                        if name_file.is_file():
                            try: theme_name = name_file.read_text(encoding="utf-8").strip()
                            except Exception as e: self.log_message(f"Warning: Could not read {name_file}")
                        if theme_name not in themes:
                            self.log_message(f"- Found: '{theme_name}'"); themes[theme_name] = Theme(theme_name, theme_dir)
        return themes

    def load_engine_paths(self):
        self._create_user_dir_if_needed(APP_ROOT, "engines", "engines")
        engines = {}
        self.log_message("Searching for engines...")
        for path in ENGINE_SEARCH_PATHS:
            if path.is_dir():
                for exe_path in path.rglob("*.exe"):
                    try:
                        engine = chess.engine.SimpleEngine.popen_uci(str(exe_path)); engine_name = engine.id['name']; engine.quit()
                        if engine_name not in engines:
                            self.log_message(f"- Found: {engine_name}"); engines[engine_name] = str(exe_path)
                    except Exception:
                        self.log_message(f"- Failed to load: {exe_path.name}")
        return engines

    def _set_interactive_widgets_state(self, parent_widget, state):
        for child in parent_widget.winfo_children():
            if isinstance(child, (tk.Button, tk.Entry, tk.Spinbox, tk.Scale, tk.OptionMenu, ttk.Notebook)):
                try: child.configure(state=state)
                except tk.TclError: pass
            self._set_interactive_widgets_state(child, state)

    def reset_ui_to_setup(self):
        if self.is_remote_game and self.remote_game:
            try:
                self.remote_game.stop()
                self.log_message("Notified server of game termination.")
            except Exception as e:
                self.log_message(f"Could not notify server of game end: {e}")

        self.quit_all_engines()
        if self.game_server:
            self.stop_game_server(confirm=False)
        self.game.reset()
        self.board.redraw_all()
        self.set_ui_state(is_game_running=False)
        self.white_player_config = None
        self.black_player_config = None
        self.remote_game = None
        self.is_remote_game = False
        self.local_player_color = None
        self.is_handling_game_end = False

    def start_game(self):
        self.log_message("--- New Game Started ---", clear=True)
        self.white_player_config = self.white_player_panel.get_player_config()
        self.black_player_config = self.black_player_panel.get_player_config()

        self.is_remote_game = self.white_player_config['type'] == 'remote' or self.black_player_config['type'] == 'remote'

        if self.is_remote_game:
            if not self._setup_remote_game():
                return

        def get_player_description(config):
            if config['type'] == 'human':
                return f"Human ({config['name']})"
            elif config['type'] == 'cpu':
                desc = f"CPU ({config.get('engine', 'N/A')}"
                if 'elo' in config:
                    desc += f" @ {config['elo']} Elo"
                desc += ")"
                return desc
            elif config['type'] == 'remote':
                return f"Remote Player ({config.get('host', 'N/A')})"
            return "Unknown"

        self.log_message(f"White: {get_player_description(self.white_player_config)}")
        self.log_message(f"Black: {get_player_description(self.black_player_config)}")
        self.log_message("-" * 20)

        self.set_ui_state(is_game_running=True)
        self.quit_all_engines()
        self.game.reset()
        
        self.active_engines["White"] = self._configure_engine(self.white_player_config)
        self.active_engines["Black"] = self._configure_engine(self.black_player_config)
        self.active_engines = {k: v for k, v in self.active_engines.items() if v}
        
        self.board.selected_square = None
        self.board.redraw_all()
        self.after(100, self.game_loop)

    def _setup_remote_game(self):
        try:
            if self.white_player_config['type'] == 'remote':
                remote_config = self.white_player_config
                local_config = self.black_player_config
                self.local_player_color = chess.BLACK
            else:
                remote_config = self.black_player_config
                local_config = self.white_player_config
                self.local_player_color = chess.WHITE

            client = GameClient(host=remote_config['host'], port=remote_config['port'], password=remote_config.get('password'), use_tls=remote_config.get('use_tls', False))
            
            if 'game_id' in remote_config:
                self.log_message(f"Joining game {remote_config['game_id']}...")
                self.remote_game = RemoteGame(remote_config['game_id'], host=remote_config['host'], port=remote_config['port'], password=remote_config.get('password'), use_tls=remote_config.get('use_tls', False))
                self.remote_game.add_player(Player(local_config['name']))
                self.log_message("Successfully joined game.")
            else:
                self.log_message("Creating new remote game...")
                self.remote_game = client.create_game(name=f"{local_config['name']}'s Game", turn_based=True, max_players=2)
                self.remote_game.add_player(Player(local_config['name']))
                self.log_message(f"Game created with ID: {self.remote_game.game_id}")

            self.remote_game.set_state({'fen': chess.STARTING_FEN})
            self.remote_game.start()
            return True

        except Exception as e:
            self.log_message(f"Error setting up remote game: {e}")
            messagebox.showerror("Remote Game Error", f"Could not set up the remote game:\n{e}")
            return False

    def _configure_engine(self, config):
        if config["type"] != "cpu": return None
        try:
            engine_process = chess.engine.SimpleEngine.popen_uci(self.engine_paths[config["engine"]])
            if "elo" in config and "UCI_Elo" in engine_process.options:
                engine_process.configure({"UCI_LimitStrength": True, "UCI_Elo": config["elo"]})
            return {"process": engine_process, "time": config["time"]}
        except Exception as e:
            self.log_message(f"Failed to start engine {config['engine']}"); return None

    def confirm_new_game(self):
        if messagebox.askyesno("New Game", "Are you sure? This will stop the current game and return to the setup screen."):
            self.reset_ui_to_setup()

    def quit_all_engines(self):
        for engine_info in self.active_engines.values():
            try: engine_info["process"].quit()
            except: pass
        self.active_engines.clear()

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"): 
            self.quit_all_engines()
            if self.game_server:
                self.game_server.stop()
            self.destroy()
    
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
        self.log_message("Requesting help...")
        def get_best_move():
            try:
                engine = chess.engine.SimpleEngine.popen_uci(self.engine_paths[self.help_engine_name])
                result = engine.play(self.game.get_board(), chess.engine.Limit(time=0.5)); engine.quit()
                self.after(0, lambda: (
                    self.log_message(f"Suggested move: {self.game.get_board().san(result.move)}"),
                    self.board.draw_help_arrow(result.move), 
                    self.help_button.config(state=tk.NORMAL)
                ))
            except Exception as e: 
                self.log_message(f"Help engine error: {e}")
                self.after(0, lambda: self.help_button.config(state=tk.NORMAL))
        threading.Thread(target=get_best_move, daemon=True).start()

    def prompt_for_pgn_save(self):
        dialog = tk.Toplevel(self)
        dialog.title("PGN Metadata")
        
        fields = {"Event": "Casual Game", "Site": "Local", "Round": ""}
        entries = {}

        for i, (field, default) in enumerate(fields.items()):
            tk.Label(dialog, text=f"{field}:").grid(row=i, column=0, padx=5, pady=5, sticky="w")
            entry = tk.Entry(dialog, width=40)
            entry.insert(0, default)
            entry.grid(row=i, column=1, padx=5, pady=5)
            entries[field] = entry

        def on_ok():
            metadata = {field: entry.get() for field, entry in entries.items()}
            dialog.destroy()
            self._save_pgn(metadata)

        ok_button = tk.Button(dialog, text="OK", command=on_ok)
        ok_button.grid(row=len(fields), column=0, columnspan=2, pady=10)
        
        dialog.transient(self)
        dialog.grab_set()
        self.wait_window(dialog)

    def _save_pgn(self, metadata):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pgn",
            filetypes=[("PGN files", "*.pgn"), ("All files", "*.*")]
        )
        if not filepath:
            return

        pgn_game = chess.pgn.Game()
        
        pgn_game.headers["Event"] = metadata.get("Event") or "?"
        pgn_game.headers["Site"] = metadata.get("Site") or "?"
        pgn_game.headers["Round"] = metadata.get("Round") or "?"
        pgn_game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
        
        if self.white_player_config:
            pgn_game.headers["White"] = self.white_player_config.get('name', 'White Player')
            if self.white_player_config['type'] == 'cpu' and 'elo' in self.white_player_config:
                pgn_game.headers["WhiteElo"] = str(self.white_player_config['elo'])

        if self.black_player_config:
            pgn_game.headers["Black"] = self.black_player_config.get('name', 'Black Player')
            if self.black_player_config['type'] == 'cpu' and 'elo' in self.black_player_config:
                pgn_game.headers["BlackElo"] = str(self.black_player_config['elo'])
        
        pgn_game.headers["Result"] = self.game.get_board().result()

        board_copy = self.game.get_board().copy()
        board_copy.reset()
        node = pgn_game
        for move in self.game.get_board().move_stack:
            node = node.add_variation(move)
            board_copy.push(move)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                exporter = chess.pgn.FileExporter(f)
                pgn_game.accept(exporter)
            self.log_message(f"Game saved to {Path(filepath).name}")
        except Exception as e:
            self.log_message(f"Error saving PGN: {e}")
            messagebox.showerror("Save Error", f"Could not save PGN file:\n{e}")
