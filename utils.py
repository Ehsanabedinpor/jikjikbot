"""
Utility functions for Jik Jik Bot
"""

import time
from datetime import datetime, timedelta
from typing import Optional


def format_time(seconds: int) -> str:
    """Format seconds to human-readable time"""
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''}"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def format_number(num: int) -> str:
    """Format number with commas"""
    return f"{num:,}"


def check_tictactoe_winner(board: str) -> Optional[int]:
    """Check for winner in Tic Tac Toe board
    Returns: 1 (player 1 wins), 2 (player 2 wins), 'draw' (draw), None (ongoing)
    Board format: 9 characters of 'X', 'O', or '-'
    """
    # Board positions: 0-8, row/col indices
    lines = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),  # rows
        (0, 3, 6), (1, 4, 7), (2, 5, 8),  # columns
        (0, 4, 8), (2, 4, 6)  # diagonals
    ]

    for line in lines:
        a, b, c = line
        if board[a] != '-' and board[a] == board[b] == board[c]:
            return 1 if board[a] == 'X' else 2

    if '-' not in board:
        return 'draw'

    return None


def make_tictactoe_move(board: str, position: int, player: int) -> str:
    """Make a move in Tic Tac Toe, return new board"""
    if player == 1:
        symbol = 'X'
    else:
        symbol = 'O'

    board_list = list(board)
    board_list[position] = symbol
    return ''.join(board_list)


def get_tictactoe_board_display(board: str, player1_id: int,
                                player2_id: int,
                                current_user_id: int) -> str:
    """Get formatted board display with emojis"""
    emoji_map = {
        'X': '❌',
        'O': '⭕',
        '-': '⬜'
    }

    display = "🎮 *Tic Tac Toe*\n\n"
    display += f"Player 1 (❌): `{player1_id}`\n"
    display += f"Player 2 (⭕): `{player2_id}`\n\n"

    # Add board
    for i in range(3):
        row = board[i * 3:(i + 1) * 3]
        row_display = ' '.join(emoji_map.get(c, '⬜') for c in row)
        display += row_display + '\n'

    display += "\n📍 Position numbers:\n"
    display += "1️⃣ 2️⃣ 3️⃣\n"
    display += "4️⃣ 5️⃣ 6️⃣\n"
    display += "7️⃣ 8️⃣ 9️⃣\n"

    if player1_id == current_user_id:
        display += "\n➡️ It's your turn! (❌)"
    elif player2_id == current_user_id:
        display += "\n➡️ It's your turn! (⭕)"

    return display


def is_user_online(user_last_seen: Optional[datetime]) -> bool:
    """Check if user is considered online (active within last 5 minutes)"""
    if not user_last_seen:
        return False
    return (datetime.now() - user_last_seen).total_seconds() < 300


def validate_command_input(text: str, expected_type: str) -> bool:
    """Validate command input"""
    if not text:
        return False

    if expected_type == 'number':
        try:
            int(text)
            return True
        except ValueError:
            return False

    return True


def escape_markdown(text: str) -> str:
    """Escape special characters for Markdown"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + '...'