# tests/test_game.py

import unittest
from domichess.core.game import Game

class TestGame(unittest.TestCase):
    """
    Tests for the Game class.
    """
    def setUp(self):
        """
        Set up a new game for each test.
        """
        self.game = Game()

    def test_initial_board(self):
        """
        Test that the board is set up correctly at the start.
        """
        self.assertEqual(self.game.get_board().fen(), "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

    def test_legal_move(self):
        """
        Test that a legal move is accepted.
        """
        self.assertTrue(self.game.move("e2e4"))
        self.assertEqual(self.game.get_board().fen(), "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")

    def test_illegal_move(self):
        """
        Test that an illegal move is rejected.
        """
        self.assertFalse(self.game.move("e2e5"))
        self.assertEqual(self.game.get_board().fen(), "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

if __name__ == "__main__":
    unittest.main()
