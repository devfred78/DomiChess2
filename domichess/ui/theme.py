# domichess/ui/theme.py

from pathlib import Path
from PIL import Image, ImageTk
import json
import chess.svg
import io
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM

class Theme:
    """
    Manages visual assets for a theme, supporting both file-based and SVG-generated pieces.
    """
    # Define default colors as CLASS attributes
    light_square_color = "#F0D9B5"
    dark_square_color = "#B58863"
    border_color = "#D4B28C"
    coordinate_color = "black"

    def __init__(self, name, path=None):
        self.name = name
        self.path = path
        self.piece_images = {}
        self.square_images = {}
        
        # Initialize instance attributes from class defaults
        self.light_square_color = Theme.light_square_color
        self.dark_square_color = Theme.dark_square_color
        self.border_color = Theme.border_color
        self.coordinate_color = Theme.coordinate_color

        if path:
            self._load_assets()

    def _load_assets(self):
        piece_map = {
            'wK': 'K', 'wQ': 'Q', 'wR': 'R', 'wB': 'B', 'wN': 'N', 'wP': 'P',
            'bK': 'k', 'bQ': 'q', 'bR': 'r', 'bB': 'b', 'bN': 'n', 'bP': 'p'
        }
        for file_prefix, piece_symbol in piece_map.items():
            image_path = self.path / f"{file_prefix}.png"
            if image_path.is_file():
                self.piece_images[piece_symbol] = Image.open(image_path).convert("RGBA")

        light_square_path = self.path / "light_square.png"
        dark_square_path = self.path / "dark_square.png"
        if light_square_path.is_file():
            self.square_images['light'] = Image.open(light_square_path).convert("RGBA")
        if dark_square_path.is_file():
            self.square_images['dark'] = Image.open(dark_square_path).convert("RGBA")
            
        colors_file = self.path / "colors.json"
        if colors_file.is_file():
            try:
                with open(colors_file, 'r') as f:
                    colors = json.load(f)
                    self.light_square_color = colors.get('light', self.light_square_color)
                    self.dark_square_color = colors.get('dark', self.dark_square_color)
                    self.border_color = colors.get('border', self.border_color)
                    self.coordinate_color = colors.get('coordinates', self.coordinate_color)
            except (IOError, json.JSONDecodeError) as e:
                print(f"Warning: Could not load or parse colors.json for theme '{self.name}': {e}")

    def get_piece_image(self, piece, size):
        if not hasattr(self, '_image_cache'): self._image_cache = {}
        cache_key = (self.name, piece.symbol(), size)
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]

        photo_image = None
        if self.name == "Default":
            svg_code = chess.svg.piece(piece, size=size)
            try:
                drawing = svg2rlg(io.StringIO(svg_code))
                png_data = renderPM.drawToString(drawing, fmt="PNG", bg=None)
                pil_image = Image.open(io.BytesIO(png_data)).convert("RGBA")
                photo_image = ImageTk.PhotoImage(pil_image)
            except Exception as e:
                print(f"Error generating SVG piece: {e}")
                return None
        else:
            # For file-based themes, get the symbol from the piece object
            piece_symbol = piece.symbol()
            if piece_symbol in self.piece_images:
                original = self.piece_images[piece_symbol]
                resized = original.resize((size, size), Image.Resampling.LANCZOS)
                photo_image = ImageTk.PhotoImage(resized)

        if photo_image:
            self._image_cache[cache_key] = photo_image
        return photo_image

    def get_square_image(self, color_type, size):
        if not hasattr(self, '_image_cache'): self._image_cache = {}
        cache_key = (self.name, color_type, size)
        if cache_key in self._image_cache: return self._image_cache[cache_key]

        if color_type in self.square_images:
            original = self.square_images[color_type]
            resized = original.resize((size, size), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(resized)
            self._image_cache[cache_key] = photo
            return photo
        return None
