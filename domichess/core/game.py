# domichess/core/game.py

import chess

class Game:
    """
    Represents the chess game logic.
    This class is a wrapper around the python-chess library.
    """
    def __init__(self):
        """
        Initializes a new game.
        """
        self.board = chess.Board()

    def reset(self):
        """
        Resets the game to the initial state.
        """
        self.board.reset()

    def move(self, uci_move):
        """
        Makes a move on the board.

        :param uci_move: The move in UCI format (e.g., "e2e4").
        :return: True if the move is legal, False otherwise.
        """
        try:
            move = chess.Move.from_uci(uci_move)
            if move in self.board.legal_moves:
                self.board.push(move)
                return True
            return False
        except ValueError:
            return False

    def get_board(self):
        """
        Returns the current board state.
        """
        return self.board

    def is_game_over(self):
        """
        Checks if the game is over.
        """
        return self.board.is_game_over()

    def get_game_result(self):
        """
        Returns the result of the game if it is over.
        """
        return self.board.result()
