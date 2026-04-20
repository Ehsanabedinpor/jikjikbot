import logging
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters
)

from config import BOT_TOKEN, BALE_API_BASE_URL, BALE_FILE_BASE_URL
from keyboards import main_menu_keyboard
from payment import (
    handle_text_and_callback,
    handle_pre_checkout_query,
    handle_successful_payment
)

logging.basicConfig(level=logging.INFO)


async def start(update, context):
    await update.message.reply_text(
        "سلام! به بات Jik Jik خوش آمدید 🎮\n\nاز منو زیر استفاده کنید:",
        reply_markup=main_menu_keyboard()
    )


def main():
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .base_url(BALE_API_BASE_URL)
        .base_file_url(BALE_FILE_BASE_URL)
        .build()
    )

    # کامند start
    application.add_handler(CommandHandler("start", start))

    # هندلر پیام‌های متنی + دکمه‌های Inline
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_and_callback))
    application.add_handler(CallbackQueryHandler(handle_text_and_callback))

    # هندلرهای پرداخت
    application.add_handler(PreCheckoutQueryHandler(handle_pre_checkout_query))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment))

    print("بات Jik Jik با موفقیت راه‌اندازی شد...")
    application.run_polling()


if __name__ == '__main__':
    main()