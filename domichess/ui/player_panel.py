# domichess/ui/player_panel.py

import tkinter as tk
from tkinter import ttk
import chess.engine
import threading

DISPLAY_PIECE_SIZE = 64

# A bit of a hack to get the multiplayer library if available
MULTIPLAYER_AVAILABLE = False
try:
    from multiplayer.client import GameClient
    MULTIPLAYER_AVAILABLE = True
except ImportError:
    pass

class PlayerPanel(tk.LabelFrame):
    """
    A panel to configure a player, showing a representative piece and a notebook.
    """
    def __init__(self, main_window, player_color, engine_paths, display_piece):
        title = f"{player_color} Player"
        super().__init__(main_window, text=title, padx=10, pady=10)

        self.main_window = main_window
        self.engine_paths = engine_paths
        self.display_piece = display_piece
        self.piece_photo_image = None
        self.selected_server = None

        # --- Main Layout using .grid() for robustness ---
        self.columnconfigure(2, weight=1) # Make the notebook column expandable

        self.piece_label = tk.Label(self)
        self.piece_label.grid(row=0, column=0, sticky="ns", padx=(0, 10))

        separator = ttk.Separator(self, orient='vertical')
        separator.grid(row=0, column=1, sticky="ns", padx=5)
        
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=0, column=2, sticky="nsew")

        # --- Human Tab ---
        self.human_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.human_frame, text='Human')
        tk.Label(self.human_frame, text="Name:").pack(side=tk.LEFT, padx=(0, 5))
        self.human_name_var = tk.StringVar(value=f"{player_color} Player")
        tk.Entry(self.human_frame, textvariable=self.human_name_var).pack(side=tk.LEFT, fill="x", expand=True)

        # --- CPU Tab ---
        self.cpu_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.cpu_frame, text='CPU')
        
        # --- Remote Tab ---
        if MULTIPLAYER_AVAILABLE:
            self.remote_frame = ttk.Frame(self.notebook, padding="10")
            self.notebook.add(self.remote_frame, text='Remote')
            self._create_remote_widgets()
        
        self.cpu_engine_var = None
        self.update_engine_list(engine_paths)


    def _create_remote_widgets(self):
        server_frame = tk.Frame(self.remote_frame)
        server_frame.pack(fill="x", pady=(0, 5))
        
        self.scan_button = tk.Button(server_frame, text="Scan Network", command=self._scan_for_servers)
        self.scan_button.pack(side=tk.LEFT)
        
        self.server_listbox = tk.Listbox(self.remote_frame, height=3)
        self.server_listbox.pack(fill="x", expand=True, pady=(0, 5))
        self.server_listbox.bind('<<ListboxSelect>>', self._on_server_selected)
        
        game_frame = tk.Frame(self.remote_frame)
        game_frame.pack(fill="x", pady=(5, 0))
        
        self.create_game_button = tk.Button(game_frame, text="Create Game", state=tk.DISABLED)
        self.create_game_button.pack(side=tk.LEFT)
        
        self.join_game_button = tk.Button(game_frame, text="Join Game", state=tk.DISABLED)
        self.join_game_button.pack(side=tk.LEFT, padx=5)
        
        self.games_listbox = tk.Listbox(self.remote_frame, height=3)
        self.games_listbox.pack(fill="x", expand=True, pady=(5, 0))
        self.games_listbox.bind('<<ListboxSelect>>', self._on_game_selected)

    def _scan_for_servers(self):
        self.scan_button.config(state=tk.DISABLED)
        self.server_listbox.delete(0, tk.END)
        self.games_listbox.delete(0, tk.END)
        self.selected_server = None
        self.main_window.log_message("Scanning for servers...")

        def discovery_thread_func():
            try:
                servers = GameClient.discover_servers(timeout=3)
                self.main_window.after(0, self._update_server_list, servers)
            except Exception as e:
                self.main_window.after(0, self.main_window.log_message, f"Discovery failed: {e}")
            finally:
                self.main_window.after(0, self.scan_button.config, {"state": tk.NORMAL})

        threading.Thread(target=discovery_thread_func, daemon=True).start()

    def _update_server_list(self, servers):
        if not servers:
            self.main_window.log_message("No servers found.")
            return
        
        self.main_window.log_message(f"Found {len(servers)} server(s):")
        for host, port in servers:
            self.server_listbox.insert(tk.END, f"{host}:{port}")
            self.main_window.log_message(f"- {host}:{port}")

    def _on_server_selected(self, event=None):
        selection = self.server_listbox.curselection()
        if not selection:
            return
        
        self.selected_server = self.server_listbox.get(selection[0])
        self.games_listbox.delete(0, tk.END)
        self.create_game_button.config(state=tk.NORMAL)
        self.join_game_button.config(state=tk.DISABLED)
        
        host, port_str = self.selected_server.split(":")
        port = int(port_str)
        
        self.main_window.log_message(f"Querying games from {self.selected_server}...")
        
        def list_games_thread_func():
            try:
                client = GameClient(host=host, port=port)
                games = client.list_games()
                self.main_window.after(0, self._update_game_list, games)
            except Exception as e:
                self.main_window.after(0, self.main_window.log_message, f"Failed to list games: {e}")

        threading.Thread(target=list_games_thread_func, daemon=True).start()

    def _update_game_list(self, games):
        self.games_listbox.delete(0, tk.END)
        if not games:
            self.main_window.log_message("No active games on this server.")
            return
        
        self.main_window.log_message(f"Found {len(games)} game(s):")
        for game_id, attributes in games.items():
            # Using a simple name for now, could be more descriptive
            game_name = attributes.get('name', game_id[:8]) 
            self.games_listbox.insert(tk.END, game_name)
            self.main_window.log_message(f"- {game_name}")

    def _on_game_selected(self, event=None):
        selection = self.games_listbox.curselection()
        if selection:
            self.join_game_button.config(state=tk.NORMAL)
        else:
            self.join_game_button.config(state=tk.DISABLED)

    def update_engine_list(self, engine_paths):
        self.engine_paths = engine_paths
        
        for widget in self.cpu_frame.winfo_children():
            widget.destroy()

        available_engines = list(engine_paths.keys())
        self.is_elo_supported = False

        if not available_engines:
            tk.Label(self.cpu_frame, text="No engines available.").pack()
            self.cpu_engine_var = None
            return

        engine_frame = tk.Frame(self.cpu_frame); engine_frame.pack(fill="x")
        tk.Label(engine_frame, text="Engine:").pack(side=tk.LEFT)
        self.cpu_engine_var = tk.StringVar(value=available_engines[0])
        self.cpu_engine_var.trace_add("write", self._on_engine_selected)
        tk.OptionMenu(engine_frame, self.cpu_engine_var, *available_engines).pack(side=tk.LEFT, fill="x", expand=True)

        time_frame = tk.Frame(self.cpu_frame); time_frame.pack(fill="x", pady=(10, 0))
        tk.Label(time_frame, text="Time (s):").pack(side=tk.LEFT)
        self.cpu_time_var = tk.DoubleVar(value=1.0)
        tk.Spinbox(time_frame, from_=0.1, to=30.0, increment=0.1, textvariable=self.cpu_time_var, width=5).pack(side=tk.LEFT)

        self.elo_frame = tk.Frame(self.cpu_frame)
        self.elo_frame.pack(fill="x", pady=(10, 0))
        self.elo_label = tk.Label(self.elo_frame, text="Elo:")
        self.elo_var = tk.IntVar()
        self.elo_value_label = tk.Label(self.elo_frame, textvariable=self.elo_var, width=4)
        self.elo_scale = tk.Scale(self.elo_frame, variable=self.elo_var, orient=tk.HORIZONTAL, showvalue=0)
        
        self.after(10, self._on_engine_selected)


    def update_piece_display(self, piece_theme):
        if not piece_theme or not self.display_piece:
            return
        
        self.piece_photo_image = piece_theme.get_piece_image(self.display_piece, DISPLAY_PIECE_SIZE)
        self.piece_label.config(image=self.piece_photo_image)

    def _on_engine_selected(self, *args):
        if not self.cpu_engine_var or not self.cpu_engine_var.get():
            return

        self.elo_label.pack_forget()
        self.elo_scale.pack_forget()
        self.elo_value_label.pack_forget()
        self.is_elo_supported = False

        engine_name = self.cpu_engine_var.get()
        engine_path = self.engine_paths.get(engine_name)
        if not engine_path: return

        try:
            engine = chess.engine.SimpleEngine.popen_uci(engine_path)
            if "UCI_Elo" in engine.options:
                self.is_elo_supported = True
                elo_option = engine.options["UCI_Elo"]
                self.elo_scale.config(from_=elo_option.min, to=elo_option.max)
                self.elo_var.set(elo_option.default)
                self.elo_label.pack(side=tk.LEFT)
                self.elo_scale.pack(side=tk.LEFT, fill="x", expand=True)
                self.elo_value_label.pack(side=tk.LEFT)
            engine.quit()
        except Exception as e:
            print(f"Could not query engine {engine_name} for options: {e}")

    def get_player_config(self):
        selected_tab = self.notebook.tab(self.notebook.select(), "text")
        
        if selected_tab == "Human":
            return {"type": "human", "name": self.human_name_var.get()}
        
        if selected_tab == "CPU":
            if self.cpu_engine_var and self.cpu_engine_var.get():
                config = {
                    "type": "cpu",
                    "name": self.cpu_engine_var.get(),
                    "engine": self.cpu_engine_var.get(),
                    "time": self.cpu_time_var.get()
                }
                if self.is_elo_supported:
                    config["elo"] = self.elo_var.get()
                return config
            return {"type": "cpu", "name": "N/A", "engine": None}

        if selected_tab == "Remote":
            config = {"type": "remote", "name": "Remote Player"}
            if self.selected_server:
                host, port_str = self.selected_server.split(":")
                config["host"] = host
                config["port"] = int(port_str)
            
            selection = self.games_listbox.curselection()
            if selection:
                config["game_name"] = self.games_listbox.get(selection[0])

            return config

        return {"type": "unknown"}

    def set_callback(self, callback):
        self.notebook.bind("<<NotebookTabChanged>>", callback)
