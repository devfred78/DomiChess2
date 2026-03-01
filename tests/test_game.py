# tests/test_game.py

import unittest
from domichess.core.game import Game
import chess

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

    def test_reset_game(self):
        """
        Test that the game is reset correctly.
        """
        self.assertTrue(self.game.move("e2e4"))
        self.game.reset()
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

    def test_invalid_uci_move(self):
        """
        Test that an invalid UCI move is rejected.
        """
        self.assertFalse(self.game.move("e2e4e5"))
        self.assertEqual(self.game.get_board().fen(), "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

    def test_checkmate(self):
        """
        Test for checkmate (Scholar's Mate).
        """
        moves = ["e2e4", "e7e5", "d1h5", "b8c6", "f1c4", "g8f6", "h5f7"]
        for move in moves:
            self.assertTrue(self.game.move(move))
        
        self.assertTrue(self.game.is_game_over())
        self.assertTrue(self.game.board.is_checkmate())
        self.assertEqual(self.game.get_game_result(), "1-0")

    def test_stalemate(self):
        """
        Test for stalemate.
        """
        # Position where the next move leads to stalemate
        self.game.board.set_fen("7k/8/8/8/8/8/4Q3/K7 w - - 0 1")
        self.assertTrue(self.game.move("e2a6"))
        self.assertTrue(self.game.is_game_over())
        self.assertTrue(self.game.board.is_stalemate())
        self.assertEqual(self.game.get_game_result(), "1/2-1/2")

    def test_castling(self):
        """
        Test castling.
        """
        # White kingside castling
        self.game.board.set_fen("rnbqk2r/pppp1ppp/5n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4")
        self.assertTrue(self.game.move("e1g1"))
        self.assertEqual(self.game.board.fen(), "rnbqk2r/pppp1ppp/5n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQ1RK1 b kq - 5 4")

    def test_pawn_promotion(self):
        """
        Test pawn promotion to a queen.
        """
        self.game.board.set_fen("8/P7/8/k7/8/8/8/K7 w - - 0 1")
        self.assertTrue(self.game.move("a7a8q"))  # Promote to queen
        self.assertEqual(self.game.board.fen(), "Q7/8/8/k7/8/8/8/K7 b - - 0 1")
        piece = self.game.board.piece_at(chess.A8)
        self.assertIsNotNone(piece)
        self.assertEqual(piece.symbol(), 'Q')

    def test_en_passant(self):
        """
        Test en passant.
        """
        self.assertTrue(self.game.move("e2e4"))
        self.assertTrue(self.game.move("a7a6"))
        self.assertTrue(self.game.move("e4e5"))
        self.assertTrue(self.game.move("d7d5"))
        self.assertTrue(self.game.move("e5d6"))  # en passant
        self.assertEqual(self.game.board.fen(), "rnbqkbnr/1ppp1ppp/p2P4/8/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 3")

if __name__ == "__main__":
    unittest.main()
