# bot.py

import logging
from telegram import Chat
from telegram.error import Forbidden, BadRequest
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, PreCheckoutQueryHandler, filters
)

from config import (
    BOT_TOKEN, BALE_API_BASE_URL, BALE_FILE_BASE_URL,
    AUTO_JIK_UNLOCK_10MIN, AUTO_JIK_UNLOCK_5MIN,
    AUTO_JIK_INTERVAL_10MIN, AUTO_JIK_INTERVAL_5MIN,
    JIK_JIK_POINTS,
)
from Db import db
from keyboards import main_menu_keyboard
from payment import handle_text_and_callback, handle_pre_checkout_query
from tictactoe_handlers import handle_tictactoe_command, handle_start_join

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== Auto Jik Jik Job ====================

async def auto_jik_job(context):
    """
    Runs every AUTO_JIK_INTERVAL_10MIN seconds.
    Gives JIK_JIK_POINTS to every eligible user and sends them a DM.
    Users with 9000+ pts get points every 5 min (handled by the faster job).
    Users with 3000+ pts get points every 10 min (this job).
    Block detection: if Forbidden → mark bot_blocked=1 in DB.
    """
    users = db.get_auto_jik_users()
    for user in users:
        user_id = user['user_id']
        points = user['points']

        # Only give to 10-min tier here (5-min tier handled by faster job)
        if points < AUTO_JIK_UNLOCK_10MIN:
            continue

        new_total = db.give_auto_jik_points(user_id, JIK_JIK_POINTS)
        db.log_event(
            user_id, 'auto_jik_grant',
            points_before=points, points_after=new_total,
            extra={'earned': JIK_JIK_POINTS, 'tier': '10min'}
        )

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"⚡ *Auto Jik Jik!* +{JIK_JIK_POINTS} امتیاز!\n\nامتیاز کل: {new_total:,}",
                parse_mode="Markdown"
            )
            # If user was previously blocked and now reachable, unblock
            if user.get('bot_blocked'):
                db.set_bot_blocked(user_id, False)
        except Forbidden:
            logger.warning(f"[AUTO_JIK] user={user_id} has blocked the bot — marking blocked")
            db.set_bot_blocked(user_id, True)
            db.log_event(user_id, 'bot_blocked', extra={'job': 'auto_jik_10min'})
        except Exception as e:
            logger.error(f"[AUTO_JIK] Failed to send to user={user_id}: {e}")


async def auto_jik_fast_job(context):
    """
    Runs every AUTO_JIK_INTERVAL_5MIN seconds.
    Only gives points to users with 9000+ pts (5-min tier).
    """
    users = db.get_auto_jik_users()
    for user in users:
        user_id = user['user_id']
        points = user['points']

        if points < AUTO_JIK_UNLOCK_5MIN:
            continue

        new_total = db.give_auto_jik_points(user_id, JIK_JIK_POINTS)
        db.log_event(
            user_id, 'auto_jik_grant',
            points_before=points, points_after=new_total,
            extra={'earned': JIK_JIK_POINTS, 'tier': '5min'}
        )

        try:
            # await context.bot.send_message(
            #     chat_id=user_id,
            #     text=f"⚡ *Auto Jik Jik!* +{JIK_JIK_POINTS} امتیاز!\n\nامتیاز کل: {new_total:,}",
            #     parse_mode="Markdown"
            # )
            if user.get('bot_blocked'):
                db.set_bot_blocked(user_id, False)
        except Forbidden:
            logger.warning(f"[AUTO_JIK_FAST] user={user_id} has blocked the bot — marking blocked")
            db.set_bot_blocked(user_id, True)
            db.log_event(user_id, 'bot_blocked', extra={'job': 'auto_jik_5min'})
        except Exception as e:
            logger.error(f"[AUTO_JIK_FAST] Failed to send to user={user_id}: {e}")


# ==================== Error Handler ====================

async def error_handler(update, context):
    error = context.error
    if isinstance(error, Forbidden):
        # User blocked the bot — find user_id from update and mark
        user_id = None
        if update and update.effective_user:
            user_id = update.effective_user.id
        if user_id:
            db.set_bot_blocked(user_id, True)
            db.log_event(user_id, 'bot_blocked', extra={'source': 'error_handler'})
            logger.warning(f"[ERROR_HANDLER] user={user_id} blocked bot (Forbidden)")
        else:
            logger.warning(f"[ERROR_HANDLER] Forbidden error but no user_id: {error}")
    elif isinstance(error, BadRequest):
        logger.warning(f"[ERROR_HANDLER] BadRequest: {error}")
    else:
        logger.error(f"[ERROR_HANDLER] Unhandled exception: {error}", exc_info=context.error)


# ==================== /start ====================

async def start(update, context):
    chat = update.effective_chat
    is_private = chat and chat.type == Chat.PRIVATE
    user = update.effective_user

    # Unblock if they message us again
    if user:
        try:
            db.set_bot_blocked(user.id, False)
        except Exception as e:
            logger.warning(f"[START] Failed to set bot_blocked: {e}")

    if context.args and context.args[0].startswith('join_'):
        if not is_private:
            await update.message.reply_text(
                "⚠️ برای پیوستن به بازی، لینک را در پیام خصوصی با بات باز کنید."
            )
            return
        await handle_start_join(update, context)
        return

    if is_private:
        db.get_or_create_user(user.id, user.username, user.first_name, user.last_name)
        # Auto-enable auto jik if eligible
        user_data = db.get_user(user.id)
        if user_data and user_data['points'] >= AUTO_JIK_UNLOCK_10MIN and not user_data['auto_jik_enabled']:
            db.enable_auto_jik(user.id)

        await update.message.reply_text(
            "سلام! به بات Jik Jik خوش آمدید 🎮\n\nاز منو زیر استفاده کنید:",
            reply_markup=main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            "👋 سلام! من بات Jik Jik هستم.\n\n"
            "📌 برای استفاده از منو، با من در پیام خصوصی صحبت کنید.\n\n"
            "🎮 *بازی دوز در گروه:*\n"
            "`/tictactoe <شرط> @نامکاربری`\n"
            "مثال: `/tictactoe 100 @ali`",
            parse_mode="Markdown"
        )


# ==================== Main ====================

def main():
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .base_url(BALE_API_BASE_URL)
        .base_file_url(BALE_FILE_BASE_URL)
        .build()
    )
    # Error handler — catches Forbidden (bot blocked) and all other errors
    application.add_error_handler(error_handler)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("tictactoe", handle_tictactoe_command))

    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_text_and_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_and_callback))
    application.add_handler(CallbackQueryHandler(handle_text_and_callback))
    application.add_handler(PreCheckoutQueryHandler(handle_pre_checkout_query))

    # Auto Jik Jik background jobs
    job_queue = application.job_queue
    job_queue.run_repeating(auto_jik_job, interval=AUTO_JIK_INTERVAL_10MIN, first=60)
    job_queue.run_repeating(auto_jik_fast_job, interval=AUTO_JIK_INTERVAL_5MIN, first=60)

    print("🚀 بات Jik Jik با موفقیت شروع شد...")
    application.run_polling()


if __name__ == '__main__':
    main()
