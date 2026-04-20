"""
Tic Tac Toe game handlers for Jik Jik Bot
"""

import logging
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Chat
from telegram.ext import ContextTypes

from Games import TicTacToeGame, get_active_game, store_game, remove_game, get_game_by_id
from Db import db
from keyboards import get_tictactoe_board_keyboard, get_back_to_menu_keyboard
from utils import format_number
from config import TICTACTOE_UNLOCK, BOT_USERNAME

logger = logging.getLogger(__name__)


def _is_private(update: Update) -> bool:
    chat = update.effective_chat
    return chat and chat.type == Chat.PRIVATE


def _new_game_id() -> int:
    return int(time.time() * 1000) % 999999


def _board_display(board: str) -> str:
    symbols = {'X': '❌', 'O': '⭕', '-': '⬜'}
    rows = []
    for i in range(3):
        row = board[i * 3:(i + 1) * 3]
        rows.append(' '.join(symbols.get(c, '⬜') for c in row))
    return '\n'.join(rows)


def _get_display_name(user_data: dict) -> str:
    if user_data:
        if user_data.get('first_name'):
            return user_data['first_name']
        if user_data.get('username'):
            return f"@{user_data['username']}"
        return str(user_data['user_id'])
    return '?'


def _game_status_text(game: TicTacToeGame) -> str:
    p1_data = db.get_user(game.player1_id)
    p2_data = db.get_user(game.player2_id) if game.player2_id else None
    p1_name = _get_display_name(p1_data) if p1_data else str(game.player1_id)
    p2_name = _get_display_name(p2_data) if p2_data else str(game.player2_id)

    text = (
        f"🎮 *بازی دوز*\n\n"
        f"❌ {p1_name}\n"
        f"⭕ {p2_name}\n"
        f"💰 شرط: {format_number(game.bet_amount)} امتیاز\n\n"
    )
    if game.status == 'active':
        if game.current_turn == game.player1_id:
            text += f"🎯 نوبت: ❌ {p1_name}"
        else:
            text += f"🎯 نوبت: ⭕ {p2_name}"
    return text


def _get_bet_keyboard() -> InlineKeyboardMarkup:
    bets = [50, 100, 200, 500, 1000]
    buttons = [InlineKeyboardButton(f"💰 {b}", callback_data=f"ttt_bet_{b}") for b in bets]
    rows = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
    rows.append([InlineKeyboardButton("◀️ بازگشت", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


def _join_link(game_id: int) -> str:
    return f"https://ble.ir/{BOT_USERNAME}?start=join_{game_id}"


async def _delete_msg(bot, chat_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


async def _send_board(bot, chat_id: int, game: TicTacToeGame, old_msg_id: int = None) -> int:
    if old_msg_id:
        await _delete_msg(bot, chat_id, old_msg_id)
    msg = await bot.send_message(
        chat_id=chat_id,
        text=_game_status_text(game),
        parse_mode="Markdown",
        reply_markup=get_tictactoe_board_keyboard(game.board, game.game_id)
    )
    return msg.message_id


# ==================== Entry Point from reply keyboard (DM only) ====================

async def handle_tictactoe_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Called when user taps 'بازی دوز 🎮' in DM"""
    if not _is_private(update):
        await update.message.reply_text(
            "🎮 برای شروع بازی دوز در گروه از دستور زیر استفاده کنید:\n"
            "`/tictactoe <شرط> @نام‌کاربری`\n\n"
            "مثال: `/tictactoe 100 @ali`",
            parse_mode="Markdown"
        )
        return

    user = update.message.from_user
    user_id = user.id
    db.get_or_create_user(user_id, user.username, user.first_name, user.last_name)
    user_data = db.get_user(user_id)
    points = user_data['points'] if user_data else 0

    if points < TICTACTOE_UNLOCK:
        await update.message.reply_text(
            f"🔒 *بازی دوز قفل است!*\n\n"
            f"برای باز کردن به {format_number(TICTACTOE_UNLOCK)} امتیاز نیاز دارید.\n"
            f"امتیاز فعلی شما: {format_number(points)}",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(
        "🎮 *بازی دوز*\n\nمقدار شرط را انتخاب کنید:",
        parse_mode="Markdown",
        reply_markup=_get_bet_keyboard()
    )


# ==================== Command Handler ====================

async def handle_tictactoe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    DM:    /tictactoe <bet>            → open invite (link)
    DM:    /tictactoe <bet> @username  → direct invite to specific user
    Group: /tictactoe <bet> @username  → REQUIRED, sends DM invite to that user
    """
    user = update.message.from_user
    user_id = user.id
    is_group = not _is_private(update)

    db.get_or_create_user(user_id, user.username, user.first_name, user.last_name)
    user_data = db.get_user(user_id)

    if not user_data or user_data['points'] < TICTACTOE_UNLOCK:
        await update.message.reply_text(
            f"🔒 برای بازی دوز به {format_number(TICTACTOE_UNLOCK)} امتیاز نیاز دارید.\n"
            f"امتیاز فعلی شما: {format_number(user_data['points'] if user_data else 0)}"
        )
        return

    # In group, @username is mandatory
    if is_group and (not context.args or len(context.args) < 2 or not context.args[1].startswith('@')):
        await update.message.reply_text(
            "❌ در گروه باید حریف را مشخص کنید!\n\n"
            "مثال: `/tictactoe 100 @ali`",
            parse_mode="Markdown"
        )
        return

    if not context.args:
        if is_group:
            await update.message.reply_text(
                "❌ مقدار شرط و نام کاربری حریف را وارد کنید!\n\n"
                "مثال: `/tictactoe 100 @ali`",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "❌ مقدار شرط را وارد کنید!\n\n"
                "مثال (دعوت عمومی): `/tictactoe 100`\n"
                "مثال (دعوت مستقیم): `/tictactoe 100 @username`",
                parse_mode="Markdown",
                reply_markup=_get_bet_keyboard()
            )
        return

    try:
        bet = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ مقدار شرط باید عدد صحیح باشد!")
        return

    if bet <= 0:
        await update.message.reply_text("❌ مقدار شرط باید بیشتر از صفر باشد!")
        return

    if user_data['points'] < bet:
        await update.message.reply_text(
            f"❌ امتیاز کافی ندارید!\n"
            f"شرط: {format_number(bet)} | موجودی: {format_number(user_data['points'])}"
        )
        return

    if get_active_game(user_id):
        await update.message.reply_text("❌ شما در حال حاضر در یک بازی هستید!")
        return

    target_username = None
    if len(context.args) >= 2 and context.args[1].startswith('@'):
        target_username = context.args[1][1:].lower()
    # Also check Telegram mention entities in the message
    elif update.message.entities:
        for entity in update.message.entities:
            if entity.type == 'mention':
                # entity text includes the @
                mention = update.message.text[entity.offset:entity.offset + entity.length]
                target_username = mention[1:].lower()  # strip @
                break

    game_id = _new_game_id()
    game = TicTacToeGame(game_id=game_id, player1_id=user_id, player2_id=0, bet_amount=bet)
    game.status = 'pending'
    game.chat_id = update.message.chat_id
    game.board_msg_ids = {}
    game.invited_user_id = None
    store_game(game)
    db.log_event(user_id, 'ttt_create',
                 chat_type='group' if is_group else 'private',
                 chat_id=update.message.chat_id,
                 extra={'game_id': game_id, 'bet': bet, 'target': target_username})

    name = _get_display_name(user_data)
    join_link = _join_link(game_id)

    if target_username:
        target_user = db.get_user_by_username(target_username)

        if not target_user:
            remove_game(game_id)
            await update.message.reply_text(
                f"❌ کاربر @{target_username} در بات ثبت نشده است.\n"
                f"ابتدا باید بات را استارت کرده باشد."
            )
            return

        target_id = target_user['user_id']

        if target_id == user_id:
            remove_game(game_id)
            await update.message.reply_text("❌ نمیتوانید خودتان را دعوت کنید!")
            return

        if get_active_game(target_id):
            remove_game(game_id)
            await update.message.reply_text(f"❌ @{target_username} در حال حاضر در یک بازی دیگر است!")
            return

        # Lock the game to this specific user
        game.invited_user_id = target_id

        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=(
                    f"🎮 *بازی دوز — دعوت مستقیم*\n\n"
                    f"👤 *{name}* شما را به بازی دعوت کرد!\n"
                    f"💰 شرط: {format_number(bet)} امتیاز\n"
                    f"🔒 فقط شما میتوانید این دعوت را بپذیرید.\n\n"
                    f"برای پذیرفتن روی لینک زیر کلیک کنید:\n"
                    f"👉 {join_link}"
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Could not DM user {target_id}: {e}")
            remove_game(game_id)
            await update.message.reply_text(
                f"❌ نمیتوان به @{target_username} پیام فرستاد.\n"
                f"شاید بات را بلاک کرده باشد."
            )
            return

        reply_text = (
            f"✅ دعوتنامه برای @{target_username} ارسال شد!\n\n"
            f"💰 شرط: {format_number(bet)} امتیاز\n\n"
            f"🔗 لینک دعوت (اگر پیام نرسید):\n{join_link}"
        )
        if is_group:
            # In group: plain text only, no inline buttons that lead to DM-only menus
            await update.message.reply_text(reply_text, parse_mode="Markdown")
        else:
            await update.message.reply_text(
                reply_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ لغو دعوت", callback_data=f"ttt_forfeit_{game_id}")
                ]])
            )
    else:
        # Open invite — DM only
        await update.message.reply_text(
            f"🎮 *بازی دوز — دعوت عمومی*\n\n"
            f"👤 *{name}* یک بازی شروع کرد!\n"
            f"💰 شرط: {format_number(bet)} امتیاز\n\n"
            f"🔗 لینک پذیرش دعوت:\n{join_link}\n\n"
            f"این لینک را برای حریف خود بفرستید 👆",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ لغو", callback_data=f"ttt_forfeit_{game_id}")
            ]])
        )


# ==================== Deep-link join via /start join_GAMEID ====================

async def handle_start_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    game_id = int(context.args[0].split('_')[1])

    db.get_or_create_user(user_id, user.username, user.first_name, user.last_name)
    game = get_game_by_id(game_id)

    if not game:
        await update.message.reply_text("❌ این بازی دیگر وجود ندارد یا منقضی شده است.")
        return
    if game.status != 'pending':
        await update.message.reply_text("❌ این بازی قبلاً شروع شده است.")
        return
    if user_id == game.player1_id:
        await update.message.reply_text("❌ شما نمیتوانید دعوت خودتان را بپذیرید!")
        return
    if get_active_game(user_id):
        await update.message.reply_text("❌ شما در حال حاضر در یک بازی دیگر هستید!")
        return

    # Enforce invited_user_id if set
    invited = getattr(game, 'invited_user_id', None)
    if invited and user_id != invited:
        await update.message.reply_text("❌ این دعوت برای شما نیست!")
        return

    player2_data = db.get_user(user_id)
    if not player2_data or player2_data['points'] < game.bet_amount:
        have = player2_data['points'] if player2_data else 0
        await update.message.reply_text(
            f"❌ امتیاز کافی ندارید!\n"
            f"نیاز: {format_number(game.bet_amount)} | موجودی: {format_number(have)}"
        )
        return

    ok1, _ = db.deduct_points(game.player1_id, game.bet_amount)
    ok2, _ = db.deduct_points(user_id, game.bet_amount)
    if not ok1 or not ok2:
        if ok1: db.add_points(game.player1_id, game.bet_amount)
        if ok2: db.add_points(user_id, game.bet_amount)
        await update.message.reply_text("❌ خطا در کسر امتیاز. لطفاً دوباره امتحان کنید.")
        return

    game.player2_id = user_id
    game.status = 'active'
    game.current_turn = game.player1_id
    if not hasattr(game, 'board_msg_ids'):
        game.board_msg_ids = {}

    p2_name = _get_display_name(player2_data)
    db.log_event(user_id, 'ttt_join', chat_type='private', chat_id=update.message.chat_id,
                 extra={'game_id': game_id, 'bet': game.bet_amount, 'opponent': game.player1_id})
    db.log_event(game.player1_id, 'ttt_join_opponent',
                 extra={'game_id': game_id, 'bet': game.bet_amount, 'opponent': user_id})

    try:
        await context.bot.send_message(
            chat_id=game.player1_id,
            text=f"✅ *{p2_name}* دعوت شما را پذیرفت! بازی شروع شد 🎮",
            parse_mode="Markdown"
        )
        mid = await _send_board(context.bot, game.player1_id, game)
        game.board_msg_ids[game.player1_id] = mid
    except Exception:
        pass

    msg = await update.message.reply_text(
        _game_status_text(game),
        parse_mode="Markdown",
        reply_markup=get_tictactoe_board_keyboard(game.board, game_id)
    )
    game.board_msg_ids[user_id] = msg.message_id


# ==================== Callback Dispatcher ====================

async def handle_tictactoe_callback(data: str, query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    if data == "ttt_noop":
        await query.answer("این خانه قبلاً انتخاب شده است!", show_alert=False)
    elif data.startswith("ttt_bet_"):
        await _handle_bet_selection(data, query, user_id, context)
    elif data.startswith("ttt_move_"):
        await _make_move(data, query, user_id, context)
    elif data.startswith("ttt_forfeit_"):
        await _forfeit_game(data, query, user_id, context)


# ==================== Bet Selection (DM inline button) ====================

async def _handle_bet_selection(data: str, query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    bet = int(data.split("_")[-1])
    db.get_or_create_user(user_id, query.from_user.username, query.from_user.first_name, query.from_user.last_name)
    user_data = db.get_user(user_id)

    if not user_data or user_data['points'] < TICTACTOE_UNLOCK:
        await query.answer("امتیاز کافی برای بازی ندارید!", show_alert=True)
        return
    if user_data['points'] < bet:
        await query.answer(f"امتیاز کافی ندارید! موجودی: {format_number(user_data['points'])}", show_alert=True)
        return
    if get_active_game(user_id):
        await query.answer("شما در حال حاضر در یک بازی هستید!", show_alert=True)
        return

    game_id = _new_game_id()
    game = TicTacToeGame(game_id=game_id, player1_id=user_id, player2_id=0, bet_amount=bet)
    game.status = 'pending'
    game.chat_id = query.message.chat_id
    game.board_msg_ids = {}
    game.invited_user_id = None
    store_game(game)

    name = _get_display_name(user_data)
    join_link = _join_link(game_id)

    await query.answer()
    await query.edit_message_text(
        f"🎮 *بازی دوز — دعوت عمومی*\n\n"
        f"👤 *{name}* یک بازی شروع کرد!\n"
        f"💰 شرط: {format_number(bet)} امتیاز\n\n"
        f"🔗 لینک پذیرش دعوت:\n{join_link}\n\n"
        f"این لینک را برای حریف خود بفرستید 👆",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ لغو", callback_data=f"ttt_forfeit_{game_id}")
        ]])
    )


# ==================== Make Move ====================

async def _make_move(data: str, query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    parts = data.split("_")
    pos = int(parts[-1])
    game_id = int(parts[-2])
    game = get_game_by_id(game_id)

    if not game:
        await query.answer("بازی یافت نشد!", show_alert=True)
        return
    if game.status != 'active':
        await query.answer("بازی تمام شده است.", show_alert=True)
        return
    if user_id not in [game.player1_id, game.player2_id]:
        await query.answer("شما در این بازی حضور ندارید!", show_alert=True)
        return
    if game.current_turn != user_id:
        await query.answer("نوبت شما نیست! صبر کنید.", show_alert=True)
        return

    success, message = game.make_move(pos)
    if not success:
        await query.answer(message, show_alert=True)
        return

    await query.answer()

    if not hasattr(game, 'board_msg_ids'):
        game.board_msg_ids = {}

    other_id = game.player2_id if user_id == game.player1_id else game.player1_id
    p_before = db.get_user(user_id)
    db.log_event(user_id, 'ttt_move',
                 extra={'game_id': game_id, 'pos': pos, 'board': game.board})

    if game.is_game_over():
        prize = game.bet_amount * 2

        if game.winner == 'draw':
            db.add_points(game.player1_id, game.bet_amount)
            db.add_points(game.player2_id, game.bet_amount)
            result_text = "🤝 *مساوی!*\n\nامتیازها به هر دو بازیکن بازگشت داده شد."
            db.log_event(game.player1_id, 'ttt_draw',
                         extra={'game_id': game_id, 'bet': game.bet_amount, 'board': game.board})
            db.log_event(game.player2_id, 'ttt_draw',
                         extra={'game_id': game_id, 'bet': game.bet_amount, 'board': game.board})
        else:
            db.add_points(game.winner, prize)
            winner_data = db.get_user(game.winner)
            winner_name = _get_display_name(winner_data) if winner_data else str(game.winner)
            loser_id = game.player2_id if game.winner == game.player1_id else game.player1_id
            result_text = f"🎉 *{winner_name} برنده شد!*\n💰 {format_number(prize)} امتیاز دریافت کرد!"
            db.log_event(game.winner, 'ttt_win',
                         extra={'game_id': game_id, 'bet': game.bet_amount, 'prize': prize, 'board': game.board})
            db.log_event(loser_id, 'ttt_loss',
                         extra={'game_id': game_id, 'bet': game.bet_amount, 'board': game.board})

        end_text = (
            f"🎮 *بازی دوز — پایان بازی*\n\n"
            f"{result_text}\n\n"
            f"{_board_display(game.board)}"
        )
        board_msg_ids = dict(game.board_msg_ids)
        remove_game(game_id)

        await query.edit_message_text(end_text, parse_mode="Markdown", reply_markup=get_back_to_menu_keyboard())
        await _delete_msg(context.bot, other_id, board_msg_ids.get(other_id))
        try:
            await context.bot.send_message(
                chat_id=other_id, text=end_text,
                parse_mode="Markdown", reply_markup=get_back_to_menu_keyboard()
            )
        except Exception:
            pass
    else:
        board_text = _game_status_text(game)
        board_kb = get_tictactoe_board_keyboard(game.board, game_id)

        await query.edit_message_text(board_text, parse_mode="Markdown", reply_markup=board_kb)
        game.board_msg_ids[user_id] = query.message.message_id

        old_other_mid = game.board_msg_ids.get(other_id)
        new_mid = await _send_board(context.bot, other_id, game, old_other_mid)
        game.board_msg_ids[other_id] = new_mid


# ==================== Forfeit ====================

async def _forfeit_game(data: str, query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    game_id = int(data.split("_")[-1])
    game = get_game_by_id(game_id)

    if not game:
        await query.answer("بازی یافت نشد!", show_alert=True)
        return

    if game.status == 'pending':
        if user_id == game.player1_id:
            remove_game(game_id)
            await query.answer()
            await query.edit_message_text("❌ دعوتنامه لغو شد.")
        else:
            await query.answer("فقط سازنده میتواند دعوت را لغو کند.", show_alert=True)
        return

    if user_id not in [game.player1_id, game.player2_id]:
        await query.answer("شما در این بازی نیستید!", show_alert=True)
        return

    success, winner_id = game.forfeit(user_id)
    if not success or not winner_id:
        await query.answer("خطا در انصراف.", show_alert=True)
        return

    prize = game.bet_amount * 2
    db.add_points(winner_id, prize)
    winner_data = db.get_user(winner_id)
    winner_name = _get_display_name(winner_data) if winner_data else str(winner_id)
    end_text = f"🏳️ *انصراف!*\n\n{winner_name} برنده شد!\n💰 {format_number(prize)} امتیاز دریافت کرد!"

    other_id = game.player2_id if user_id == game.player1_id else game.player1_id
    board_msg_ids = dict(getattr(game, 'board_msg_ids', {}))
    remove_game(game_id)

    await query.answer()
    await query.edit_message_text(end_text, parse_mode="Markdown", reply_markup=get_back_to_menu_keyboard())
    await _delete_msg(context.bot, other_id, board_msg_ids.get(other_id))
    try:
        await context.bot.send_message(
            chat_id=other_id, text=end_text,
            parse_mode="Markdown", reply_markup=get_back_to_menu_keyboard()
        )
    except Exception:
        pass
