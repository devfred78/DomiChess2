# domichess/ui/player_panel.py

import tkinter as tk
from tkinter import ttk
import chess.engine

DISPLAY_PIECE_SIZE = 64

class PlayerPanel(tk.LabelFrame):
    """
    A panel to configure a player, showing a representative piece and a notebook.
    """
    def __init__(self, parent, player_color, engine_paths, display_piece):
        title = f"{player_color} Player"
        super().__init__(parent, text=title, padx=10, pady=10)

        self.engine_paths = engine_paths
        self.display_piece = display_piece
        self.piece_photo_image = None

        # --- Main Layout using .grid() for robustness ---
        self.columnconfigure(2, weight=1) # Make the notebook column expandable

        self.piece_label = tk.Label(self)
        self.piece_label.grid(row=0, column=0, sticky="ns", padx=(0, 10))

        separator = ttk.Separator(self, orient='vertical')
        separator.grid(row=0, column=1, sticky="ns", padx=5)
        
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=0, column=2, sticky="nsew")

        # --- Human Tab ---
        human_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(human_frame, text='Human')
        tk.Label(human_frame, text="Name:").pack(side=tk.LEFT, padx=(0, 5))
        self.human_name_var = tk.StringVar(value=f"{player_color} Player")
        tk.Entry(human_frame, textvariable=self.human_name_var).pack(side=tk.LEFT, fill="x", expand=True)

        # --- CPU Tab ---
        cpu_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(cpu_frame, text='CPU')

        available_engines = list(engine_paths.keys())
        self.is_elo_supported = False
        if not available_engines:
            tk.Label(cpu_frame, text="No engines available.").pack()
            self.cpu_engine_var = None
        else:
            engine_frame = tk.Frame(cpu_frame); engine_frame.pack(fill="x")
            tk.Label(engine_frame, text="Engine:").pack(side=tk.LEFT)
            self.cpu_engine_var = tk.StringVar(value=available_engines[0])
            self.cpu_engine_var.trace_add("write", self._on_engine_selected)
            tk.OptionMenu(engine_frame, self.cpu_engine_var, *available_engines).pack(side=tk.LEFT, fill="x", expand=True)

            time_frame = tk.Frame(cpu_frame); time_frame.pack(fill="x", pady=(10, 0))
            tk.Label(time_frame, text="Time (s):").pack(side=tk.LEFT)
            self.cpu_time_var = tk.DoubleVar(value=1.0)
            tk.Spinbox(time_frame, from_=0.1, to=30.0, increment=0.1, textvariable=self.cpu_time_var, width=5).pack(side=tk.LEFT)

            self.elo_frame = tk.Frame(cpu_frame)
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
                print(f"  Engine '{engine_name}' supports Elo: min={elo_option.min}, max={elo_option.max}, default={elo_option.default}")
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
        
        if self.cpu_engine_var:
            config = {
                "type": "cpu",
                "name": self.cpu_engine_var.get(),
                "engine": self.cpu_engine_var.get(),
                "time": self.cpu_time_var.get()
            }
            if self.is_elo_supported:
                config["elo"] = self.elo_var.get()
            return config
        
        return {"type": "cpu", "name": "N/A"}

    def set_callback(self, callback):
        self.notebook.bind("<<NotebookTabChanged>>", callback)
