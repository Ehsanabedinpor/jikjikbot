"""
Inline and Reply keyboards for Jik Jik Bot
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


# ====================== REPLY KEYBOARD ======================

def main_menu_keyboard():
    keyboard = [
        [KeyboardButton("پروفایل 👤"), KeyboardButton("خرید آیتم 🛒")],
        [KeyboardButton("تخم‌مرغ‌های من 🥚"), KeyboardButton("حیوانات من 🐾")],
        [KeyboardButton("بازی دوز 🎮"), KeyboardButton("پرداخت 💰")],
        [KeyboardButton("راهنما ❓")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, selective=True)


# ====================== INLINE KEYBOARDS ======================

def get_main_menu_inline():
    """منوی اصلی به صورت Inline — برای استفاده در edit_message_text"""
    keyboard = [
        [InlineKeyboardButton("پروفایل 👤", callback_data="show_profile"),
         InlineKeyboardButton("خرید آیتم 🛒", callback_data="show_buy")],
        [InlineKeyboardButton("تخم‌مرغ‌های من 🥚", callback_data="my_eggs"),
         InlineKeyboardButton("حیوانات من 🐾", callback_data="show_animals")],
        [InlineKeyboardButton("بازی دوز 🎮", callback_data="ttt_menu"),
         InlineKeyboardButton("پرداخت 💰", callback_data="main_payment")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_profile_keyboard():
    keyboard = [
        [InlineKeyboardButton("💰 دریافت امتیاز Auto Jik Jik", callback_data="claim_auto_jik")],
        [InlineKeyboardButton("◀️ بازگشت به منو", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_buy_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🥚 خرید ۱ تخم‌مرغ (۵۰۰ امتیاز)", callback_data="buy_egg_1")],
        [InlineKeyboardButton("🥚🥚 خرید ۲ تخم‌مرغ (۱۰۰۰ امتیاز)", callback_data="buy_egg_2")],
        [InlineKeyboardButton("🏷️ نام‌گذاری حیوان (۱۵۰۰ امتیاز)", callback_data="name_animal")],
        [InlineKeyboardButton("◀️ بازگشت", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_payment_keyboard():
    keyboard = [
        [InlineKeyboardButton("💎 ۱٬۰۰۰ امتیاز — ۵٬۰۰۰ تومان", callback_data="pay_1000")],
        [InlineKeyboardButton("💎 ۵٬۰۰۰ امتیاز — ۲۵٬۰۰۰ تومان", callback_data="pay_5000")],
        [InlineKeyboardButton("🥚 ۱ تخم‌مرغ — ۱۵٬۰۰۰ تومان", callback_data="pay_egg")],
        [InlineKeyboardButton("🥚🥚 ۲ تخم‌مرغ — ۲۸٬۰۰۰ تومان", callback_data="pay_2eggs")],
        [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_tictactoe_board_keyboard(board: str, game_id: int) -> InlineKeyboardMarkup:
    symbols = {'X': '❌', 'O': '⭕', '-': '⬜'}
    keyboard = []
    for row in range(3):
        row_buttons = []
        for col in range(3):
            pos = row * 3 + col
            cell = board[pos]
            symbol = symbols.get(cell, '⬜')
            callback = f"ttt_move_{game_id}_{pos}" if cell == '-' else "ttt_noop"
            row_buttons.append(InlineKeyboardButton(symbol, callback_data=callback))
        keyboard.append(row_buttons)
    keyboard.append([InlineKeyboardButton("🏳️ انصراف از بازی", callback_data=f"ttt_forfeit_{game_id}")])
    return InlineKeyboardMarkup(keyboard)


def get_back_to_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ بازگشت به منو", callback_data="main_menu")]
    ])


def get_egg_hatching_keyboard(eggs_count: int):
    keyboard = []
    if eggs_count >= 2:
        keyboard.append([
            InlineKeyboardButton("🐔 جوجه‌کشی مرغ", callback_data="hatch_chicken"),
            InlineKeyboardButton("🐓 جوجه‌کشی خروس", callback_data="hatch_rooster"),
        ])
    keyboard.append([InlineKeyboardButton("◀️ بازگشت", callback_data="my_eggs")])
    return InlineKeyboardMarkup(keyboard)


def get_animals_list_keyboard(animals: list):
    keyboard = []
    for animal in animals:
        emoji = "🐔" if animal['animal_type'] == 'chicken' else "🐓"
        name = animal['name'] if animal['name'] else "بی‌نام"
        keyboard.append([InlineKeyboardButton(f"{emoji} {name}", callback_data=f"animal_detail_{animal['id']}")])
    keyboard.append([InlineKeyboardButton("◀️ بازگشت", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)
