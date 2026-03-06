# tests/test_multiplayer.py

import unittest
from unittest.mock import patch, MagicMock, ANY
import tkinter as tk
import sys
from pathlib import Path

# This is a bit of a hack to ensure the main app path is available for imports
APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_ROOT))

# We need to mock the multiplayer library before it's imported by the UI
# Assume MULTIPLAYER_AVAILABLE is True for these tests
mock_game_client = MagicMock()
mock_game_client.discover_servers.return_value = [('192.168.1.100', 65432)]
mock_game_client.return_value.list_games.return_value = {'game-123': {'name': 'Test Game'}}

mock_remote_game = MagicMock()
mock_remote_game.state = {'fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'}
mock_game_client.return_value.create_game.return_value = mock_remote_game

mock_game_server = MagicMock()

# The path needs to point to the *actual* location of the multiplayer library
# so that the sys.path modification in main_window.py works correctly in the test environment.
# We then patch the modules *after* the import system has found them.
MULTIPLAYER_PATH = APP_ROOT.parent / "multiplayer"
if MULTIPLAYER_PATH.exists():
    sys.path.insert(0, str(MULTIPLAYER_PATH))
    MODULE_PATCHES = {
        'multiplayer.client.GameClient': mock_game_client,
        'multiplayer.server.GameServer': mock_game_server,
        'multiplayer.client.RemoteGame': mock_remote_game,
    }
else:
    # If the library isn't there, we can't run the tests, but we avoid a crash.
    MODULE_PATCHES = {}

with patch.dict('sys.modules', MODULE_PATCHES):
    from domichess.ui.main_window import MainWindow


class TestMultiplayer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up a root window for all tests."""
        cls.root = tk.Tk()
        cls.root.withdraw() # Hide the window

    @classmethod
    def tearDownClass(cls):
        """Destroy the root window."""
        cls.root.destroy()

    def setUp(self):
        """Set up a new main window for each test."""
        self.main_window = MainWindow()
        self.white_panel = self.main_window.white_player_panel
        self.black_panel = self.main_window.black_player_panel

    def tearDown(self):
        """Destroy the main window after each test."""
        self.main_window.destroy()

    @patch('threading.Thread')
    def test_scan_for_servers(self, mock_thread):
        """Test that scanning for servers populates the listbox."""
        self.white_panel._scan_for_servers()
        thread_target = mock_thread.call_args.kwargs['target']
        thread_target()
        mock_game_client.discover_servers.assert_called_once()
        self.main_window.update_idletasks()
        self.assertEqual(self.white_panel.server_listbox.get(0), '192.168.1.100:65432')

    @patch('threading.Thread')
    def test_list_games_on_server_select(self, mock_thread):
        """Test that selecting a server lists the available games."""
        self.white_panel.server_listbox.insert(tk.END, '192.168.1.100:65432')
        self.white_panel.server_listbox.selection_set(0)
        self.white_panel._on_server_selected()
        thread_target = mock_thread.call_args.kwargs['target']
        thread_target()
        mock_game_client.return_value.list_games.assert_called_once()
        self.main_window.update_idletasks()
        self.assertEqual(self.white_panel.games_listbox.get(0), 'Test Game')

    @patch('threading.Thread')
    def test_remote_game_state_sync(self, mock_thread):
        """Test sending and receiving remote game state."""
        # 1. Configure a remote vs human game
        self.white_panel.notebook.select(self.white_panel.remote_frame)
        self.white_panel.server_listbox.insert(tk.END, '192.168.1.100:65432')
        self.white_panel.server_listbox.selection_set(0)
        self.white_panel._on_server_selected() # To set the selected_server
        
        self.black_panel.notebook.select(self.black_panel.human_frame)

        # 2. Start the game
        self.main_window.start_game()
        self.main_window.update_idletasks()

        # Check that a remote game was created
        mock_game_client.return_value.create_game.assert_called_once()
        self.assertTrue(self.main_window.is_remote_game)
        self.assertIsNotNone(self.main_window.remote_game)

        # 3. Simulate a local move by the black player
        initial_fen = self.main_window.game.get_board().fen()
        self.main_window.game.get_board().push_uci("e7e5") # Manually push a move for black
        self.main_window.on_human_move("e7e5")
        
        # Check that the state was sent to the server
        # The actual call is in a thread, so we check the mock
        thread_target = mock_thread.call_args.kwargs['target']
        thread_target()
        
        final_fen = self.main_window.game.get_board().fen()
        mock_remote_game.set_state.assert_called_with({'fen': final_fen})
        self.assertNotEqual(initial_fen, final_fen)

        # 4. Simulate receiving a new state from the server
        new_remote_fen = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1"
        mock_remote_game.state = {'fen': new_remote_fen}

        # Trigger the game loop to fetch the state
        self.main_window.fetch_remote_state()
        
        # The fetch is also in a thread
        thread_target = mock_thread.call_args.kwargs['target']
        thread_target()

        # Process the UI update
        self.main_window.update_idletasks()
        
        # Check that the board was updated
        self.assertEqual(self.main_window.game.get_board().fen(), new_remote_fen)


if __name__ == "__main__":
    unittest.main()
