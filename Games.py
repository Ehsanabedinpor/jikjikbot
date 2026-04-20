"""
Game logic for Jik Jik Bot
"""

from typing import Optional, Tuple
from utils import check_tictactoe_winner


class TicTacToeGame:
    """Tic Tac Toe game logic"""

    def __init__(self, game_id: int, player1_id: int, player2_id: int,
                 bet_amount: int, board: str = "---------"):
        self.game_id = game_id
        self.player1_id = player1_id
        self.player2_id = player2_id
        self.bet_amount = bet_amount
        self.board = board
        self.current_turn = player1_id
        self.status = 'active'
        self.winner = None
        self.chat_id = None
        self.message_id = None

    def get_current_player_number(self) -> int:
        """Get current player number (1 or 2)"""
        if self.current_turn == self.player1_id:
            return 1
        return 2

    def make_move(self, position: int) -> Tuple[bool, str]:
        """Make a move at position (0-8)
        Returns: (success, message)
        """
        # Validate position
        if position < 0 or position > 8:
            return False, "Invalid position! Use 0-8."

        # Check if position is available
        if self.board[position] != '-':
            return False, "That position is already taken!"

        # Check if it's the user's turn
        if self.current_turn not in [self.player1_id, self.player2_id]:
            return False, "Invalid turn!"

        # Make the move
        current_player_num = self.get_current_player_number()
        symbol = 'X' if current_player_num == 1 else 'O'

        board_list = list(self.board)
        board_list[position] = symbol
        self.board = ''.join(board_list)

        # Check for winner
        result = check_tictactoe_winner(self.board)

        if result == 1:
            self.winner = self.player1_id
            self.status = 'completed'
            return True, f"🎉 Player 1 (❌) wins!\n\nThe {self.bet_amount} points have been added to their balance!"
        elif result == 2:
            self.winner = self.player2_id
            self.status = 'completed'
            return True, f"🎉 Player 2 (⭕) wins!\n\nThe {self.bet_amount} points have been added to their balance!"
        elif result == 'draw':
            self.status = 'completed'
            self.winner = 'draw'
            return True, f"🤝 It's a draw!\n\nThe {self.bet_amount} points have been returned to both players!"

        # Switch turns
        self.current_turn = self.player2_id if self.current_turn == self.player1_id else self.player1_id

        return True, "Move successful!"

    def is_valid_position(self, position: int) -> bool:
        """Check if position is valid and available"""
        if position < 0 or position > 8:
            return False
        return self.board[position] == '-'

    def get_winner_id(self) -> Optional[int]:
        """Get winner ID or None if no winner"""
        return self.winner

    def is_game_over(self) -> bool:
        """Check if game is over"""
        return self.status != 'active'

    def forfeit(self, player_id: int) -> Tuple[bool, Optional[int]]:
        """Player forfeits the game
        Returns: (success, winner_id)
        """
        if self.status != 'active':
            return False, None

        if player_id == self.player1_id:
            self.winner = self.player2_id
        elif player_id == self.player2_id:
            self.winner = self.player1_id
        else:
            return False, None

        self.status = 'forfeit'
        return True, self.winner

    def to_dict(self) -> dict:
        """Convert game to dictionary"""
        return {
            'game_id': self.game_id,
            'player1_id': self.player1_id,
            'player2_id': self.player2_id,
            'bet_amount': self.bet_amount,
            'board': self.board,
            'current_turn': self.current_turn,
            'status': self.status,
            'winner': self.winner
        }


# Active games storage (in production, use Redis or database)
active_games = {}


def get_active_game(user_id: int) -> Optional[TicTacToeGame]:
    """Get active game for a user"""
    for game in active_games.values():
        if user_id in [game.player1_id, game.player2_id]:
            if game.status == 'active':
                return game
    return None


def store_game(game: TicTacToeGame):
    """Store a game"""
    active_games[game.game_id] = game


def remove_game(game_id: int):
    """Remove a game"""
    if game_id in active_games:
        del active_games[game_id]


def get_game_by_id(game_id: int) -> Optional[TicTacToeGame]:
    """Get game by ID"""
    return active_games.get(game_id)