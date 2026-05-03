"""
Payment Module for Bale Bot
"""

import logging, re

from telegram import Update, LabeledPrice
from telegram.ext import ContextTypes

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


from config import (
    PAYMENT_PROVIDER_TOKEN, MESSAGES,
    EGG_COST_1, EGG_COST_2, NAMING_COST,
    TICTACTOE_UNLOCK,
)
from Db import db
from utils import format_number
from keyboards import (
    get_payment_keyboard, main_menu_keyboard, get_main_menu_inline,
    get_profile_keyboard, get_buy_menu_keyboard,
    get_egg_hatching_keyboard, get_animals_list_keyboard,
    get_back_to_menu_keyboard,
)


def normalize(text: str) -> str:
    t = text.strip().lower()
    t = t.replace("‌", " ")   # نیم‌فاصله به فاصله
    t = t.replace("\u200c", " ")  # zero-width non-joiner
    t = re.sub(r"\s+", " ", t)  # حذف فاصله‌های اضافه
    return t

logger = logging.getLogger(__name__)


def _is_private(update: Update) -> bool:
    chat = update.effective_chat
    return chat and chat.type == "private"


def _chat_type(update: Update) -> str:
    chat = update.effective_chat
    return chat.type if chat else "unknown"


def _chat_id(update: Update) -> int:
    chat = update.effective_chat
    return chat.id if chat else None


def toman_to_rial(toman: int) -> int:
    return toman * 10


async def send_invoice(chat_id, title, description, payload, prices, context):
    labeled_prices = [LabeledPrice(label=p['label'], amount=p['amount']) for p in prices]
    await context.bot.send_invoice(
        chat_id=chat_id, title=title, description=description,
        payload=payload, provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="IRR", prices=labeled_prices,
    )


async def send_points_invoice(chat_id, points, price_toman, context):
    await send_invoice(
        chat_id,
        f"💎 {format_number(points)} امتیاز",
        f"خرید {format_number(points)} امتیاز",
        f"pkg_points_{points}",
        [{'label': f'💎 {points} امتیاز', 'amount': toman_to_rial(price_toman)}],
        context
    )


async def send_egg_invoice(chat_id, egg_count, price_toman, context):
    await send_invoice(
        chat_id,
        f"🥚 {egg_count} تخم مرغ",
        f"خرید {egg_count} تخم مرغ",
        f"pkg_egg_{egg_count}",
        [{'label': f'🥚 {egg_count} تخم مرغ', 'amount': toman_to_rial(price_toman)}],
        context
    )


async def handle_pre_checkout_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    logger.info(f"[PRE_CHECKOUT] user={query.from_user.id} payload={query.invoice_payload}")
    await query.answer(ok=True)


async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    user_id = update.message.from_user.id
    payload = payment.invoice_payload
    charge_id = payment.telegram_payment_charge_id
    total_amount = payment.total_amount  # in smallest currency unit (rial)
    price_toman = total_amount // 10

    logger.info(f"[PAYMENT_SUCCESS] user={user_id} payload={payload} charge={charge_id} amount={total_amount}")

    db.get_or_create_user(user_id, update.message.from_user.username,
                          update.message.from_user.first_name, update.message.from_user.last_name)
    user_before = db.get_user(user_id)

    if payload.startswith("pkg_points_"):
        try:
            points = int(payload.split("_")[-1])
        except ValueError:
            points = 0
        if points > 0:
            new_total = db.add_points(user_id, points)
            # Record payment
            db.record_payment(user_id, payload, 'points', points, price_toman, charge_id)
            # Log event
            db.log_event(
                user_id, 'payment_success',
                chat_type='private', chat_id=update.message.chat_id,
                points_before=user_before['points'], points_after=new_total,
                extra={'payload': payload, 'charge_id': charge_id,
                       'points_bought': points, 'price_toman': price_toman}
            )
            await update.message.reply_text(
                f"✅ پرداخت موفق!\n\n"
                f"💎 {format_number(points)} امتیاز به حساب شما اضافه شد.\n"
                f"🏆 امتیاز کل: {format_number(new_total)}\n\n"
                f"شناسه تراکنش: `{charge_id}`",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        else:
            logger.error(f"[PAYMENT_ERROR] invalid points in payload={payload}")
            await update.message.reply_text("❌ خطا در پردازش پرداخت. لطفاً با پشتیبانی تماس بگیرید.")

    elif payload.startswith("pkg_egg_"):
        try:
            egg_count = int(payload.split("_")[-1])
        except ValueError:
            egg_count = 0
        if egg_count > 0:
            eggs_before = user_before['eggs']
            new_total = db.add_egg(user_id, egg_count)
            # Record payment
            db.record_payment(user_id, payload, 'egg', egg_count, price_toman, charge_id)
            # Log event
            db.log_event(
                user_id, 'buy_egg_payment',
                chat_type='private', chat_id=update.message.chat_id,
                points_before=user_before['points'], points_after=user_before['points'],
                eggs_before=eggs_before, eggs_after=new_total,
                extra={'payload': payload, 'charge_id': charge_id,
                       'eggs_bought': egg_count, 'price_toman': price_toman}
            )
            await update.message.reply_text(
                f"✅ پرداخت موفق!\n\n"
                f"🥚 {egg_count} تخم مرغ به حساب شما اضافه شد.\n"
                f"🥚 تعداد کل: {new_total}\n\n"
                f"شناسه تراکنش: `{charge_id}`",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        else:
            logger.error(f"[PAYMENT_ERROR] invalid egg_count in payload={payload}")
            await update.message.reply_text("❌ خطا در پردازش پرداخت. لطفاً با پشتیبانی تماس بگیرید.")
    else:
        logger.warning(f"[PAYMENT_UNKNOWN] user={user_id} payload={payload}")
        await update.message.reply_text(
            f"✅ پرداخت دریافت شد اما نوع سفارش شناخته نشد.\n"
            f"شناسه تراکنش: `{charge_id}`\nلطفاً با پشتیبانی تماس بگیرید.",
            parse_mode="Markdown"
        )


# ==================== هندلر اصلی ====================

async def handle_text_and_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.callback_query:
        query = update.callback_query
        data = query.data
        user = query.from_user
        user_id = user.id
        db.get_or_create_user(user_id, user.username, user.first_name, user.last_name)
        # User is interacting — they haven't blocked us
        db.set_bot_blocked(user_id, False)
        chat = query.message.chat if query.message else None
        in_group = chat and chat.type in ('group', 'supergroup')
        
        if data.startswith("transfer_"):
            parts = data.split('_', 2)   # transfer_confirm_<id> or transfer_cancel_<id>
            if len(parts) < 3:
                await query.answer("خطا")
                return
            action = parts[1]
            transfer_id = parts[2]
            transfers = context.bot_data.get('transfers', {})
            info = transfers.get(transfer_id)
            if not info:
                await query.answer("درخواست منقضی شده یا وجود ندارد.")
                return
            if query.from_user.id != info['sender_id']:
                await query.answer("⛔ این دکمه متعلق به شما نیست.", show_alert=True)
                return

            if action == 'cancel':
                del transfers[transfer_id]
                await query.edit_message_text("❌ انتقال لغو شد.", reply_markup=None)
            elif action == 'confirm':
                sender_id = info['sender_id']
                receiver_id = info['receiver_id']
                amount = info['amount']
                sender = db.get_user(sender_id)
                if not sender or sender['points'] < amount:
                    await query.edit_message_text("❌ موجودی کافی نیست. انتقال لغو شد.", reply_markup=None)
                    del transfers[transfer_id]
                    return
                success, remaining = db.deduct_points(sender_id, amount)
                if not success:
                    await query.edit_message_text("❌ خطا در انتقال.", reply_markup=None)
                    del transfers[transfer_id]
                    return
                db.add_points(receiver_id, amount)
                # Log events
                db.log_event(sender_id, 'transfer_out',
                             points_before=sender['points'], points_after=remaining,
                             extra={'to': receiver_id, 'amount': amount})
                db.log_event(receiver_id, 'transfer_in',
                             points_before=db.get_user(receiver_id)['points'] - amount,
                             points_after=db.get_user(receiver_id)['points'],
                             extra={'from': sender_id, 'amount': amount})
                await query.edit_message_text(
                    f"✅ انتقال با موفقیت انجام شد!\n{format_number(amount)} امتیاز به @{info['receiver_username']} ارسال شد.",
                    reply_markup=None)
                # Notify receiver in DM
                try:
                    await context.bot.send_message(
                        receiver_id,
                        f"💰 شما {format_number(amount)} امتیاز از @{query.from_user.username or query.from_user.id} دریافت کردید!"
                    )
                except Exception:
                    pass
                del transfers[transfer_id]
            await query.answer()
            return

        # ttt_ callbacks work everywhere (game is played in DM anyway)
        if data.startswith("ttt_"):
            from tictactoe_handlers import handle_tictactoe_callback
            await handle_tictactoe_callback(data, query, user_id, context)
            return

        # All other callbacks are DM-only — if triggered from group, tell user to go to DM
        if in_group:
            await query.answer(
                "❗️ این بخش فقط در پیام خصوصی کار میکند. با بات در DM صحبت کنید.",
                show_alert=True
            )
            return

        await query.answer()

        if data == "main_menu":
            await query.edit_message_text("🏠 منوی اصلی:", reply_markup=get_main_menu_inline())

        elif data == "ttt_menu":
            from tictactoe_handlers import _get_bet_keyboard, TICTACTOE_UNLOCK
            user_data = db.get_user(user_id)
            points = user_data['points'] if user_data else 0
            if points < TICTACTOE_UNLOCK:
                await query.edit_message_text(
                    f"🔒 *بازی دوز قفل است!*\n\n"
                    f"برای باز کردن به {format_number(TICTACTOE_UNLOCK)} امتیاز نیاز دارید.\n"
                    f"امتیاز فعلی شما: {format_number(points)}",
                    parse_mode="Markdown",
                    reply_markup=get_back_to_menu_keyboard()
                )
            else:
                await query.edit_message_text(
                    "🎮 *بازی دوز*\n\nمقدار شرط را انتخاب کنید:",
                    parse_mode="Markdown",
                    reply_markup=_get_bet_keyboard()
                )

        elif data == "show_profile":
            user_data = db.get_user(user_id)
            if not user_data:
                await query.edit_message_text("❌ خطا در دریافت پروفایل.", reply_markup=get_back_to_menu_keyboard())
                return
            pending = db.get_pending_auto_jik(user_id)
            auto_status = "✅ فعال" if user_data['auto_jik_enabled'] else "❌ غیرفعال"
            await query.edit_message_text(
                f"👤 *پروفایل شما*\n\n"
                f"🏆 امتیاز: {format_number(user_data['points'])}\n"
                f"🥚 تخم مرغ: {user_data['eggs']}\n"
                f"🐔 مرغ: {user_data['chickens']}\n"
                f"🐓 خروس: {user_data['roosters']}\n"
                f"⚡ Auto Jik Jik: {auto_status}\n"
                f"🎁 امتیاز معلق: {format_number(pending)}",
                parse_mode="Markdown",
                reply_markup=get_profile_keyboard()
            )

        elif data == "show_buy":
            await query.edit_message_text(
                "🛒 *منوی خرید*\n\nیکی از گزینهها را انتخاب کنید:",
                parse_mode="Markdown",
                reply_markup=get_buy_menu_keyboard()
            )

        elif data == "main_payment":
            await query.edit_message_text(
                "💰 لطفاً یکی از پکیجها را انتخاب کنید:",
                reply_markup=get_payment_keyboard()
            )

        elif data == "pay_1000":
            db.log_event(user_id, 'payment_initiated', extra={'package': 'points_1000'})
            await send_points_invoice(user_id, 1000, 5000, context)

        elif data == "pay_5000":
            db.log_event(user_id, 'payment_initiated', extra={'package': 'points_5000'})
            await send_points_invoice(user_id, 5000, 25000, context)

        elif data == "pay_egg":
            db.log_event(user_id, 'payment_initiated', extra={'package': 'egg_1'})
            await send_egg_invoice(user_id, 1, 15000, context)

        elif data == "pay_2eggs":
            db.log_event(user_id, 'payment_initiated', extra={'package': 'egg_2'})
            await send_egg_invoice(user_id, 2, 28000, context)

        elif data == "buy_egg_1":
            user_data = db.get_user(user_id)
            pts_before = user_data['points'] if user_data else 0
            eggs_before = user_data['eggs'] if user_data else 0
            success, remaining = db.deduct_points(user_id, EGG_COST_1)
            if success:
                db.add_egg(user_id, 1)
                user_after = db.get_user(user_id)
                # Record payment (in-app, price_toman=0)
                db.record_payment(user_id, 'buy_egg_1', 'egg', 1, 0)
                db.log_event(
                    user_id, 'buy_egg_points',
                    points_before=pts_before, points_after=remaining,
                    eggs_before=eggs_before, eggs_after=user_after['eggs'],
                    extra={'cost': EGG_COST_1, 'count': 1}
                )
                await query.edit_message_text(
                    f"✅ یک تخم مرغ خریدید!\nامتیاز باقیمانده: {format_number(remaining)}",
                    reply_markup=get_back_to_menu_keyboard()
                )
            else:
                db.log_event(user_id, 'buy_egg_failed',
                             points_before=pts_before, points_after=pts_before,
                             extra={'cost': EGG_COST_1, 'reason': 'insufficient_points'})
                await query.edit_message_text(
                    f"❌ امتیاز کافی ندارید!\nنیاز: {format_number(EGG_COST_1)} | موجودی: {format_number(remaining)}",
                    reply_markup=get_back_to_menu_keyboard()
                )

        elif data == "buy_egg_2":
            user_data = db.get_user(user_id)
            pts_before = user_data['points'] if user_data else 0
            eggs_before = user_data['eggs'] if user_data else 0
            success, remaining = db.deduct_points(user_id, EGG_COST_2)
            if success:
                db.add_egg(user_id, 2)
                user_after = db.get_user(user_id)
                db.record_payment(user_id, 'buy_egg_2', 'egg', 2, 0)
                db.log_event(
                    user_id, 'buy_egg_points',
                    points_before=pts_before, points_after=remaining,
                    eggs_before=eggs_before, eggs_after=user_after['eggs'],
                    extra={'cost': EGG_COST_2, 'count': 2}
                )
                await query.edit_message_text(
                    f"✅ دو تخم مرغ خریدید!\nامتیاز باقیمانده: {format_number(remaining)}",
                    reply_markup=get_back_to_menu_keyboard()
                )
            else:
                db.log_event(user_id, 'buy_egg_failed',
                             points_before=pts_before, points_after=pts_before,
                             extra={'cost': EGG_COST_2, 'reason': 'insufficient_points'})
                await query.edit_message_text(
                    f"❌ امتیاز کافی ندارید!\nنیاز: {format_number(EGG_COST_2)} | موجودی: {format_number(remaining)}",
                    reply_markup=get_back_to_menu_keyboard()
                )

        elif data == "hatch_chicken":
            user_data = db.get_user(user_id)
            if user_data and user_data['eggs'] >= 2:
                db.deduct_eggs(user_id, 2)
                db.add_animal(user_id, 'chicken')
                db.log_event(user_id, 'hatch_chicken',
                             eggs_before=user_data['eggs'], eggs_after=user_data['eggs'] - 2,
                             extra={'animal': 'chicken'})
                await query.edit_message_text("🐔 جوجه کشی موفق! یک مرغ اضافه شد.", reply_markup=get_back_to_menu_keyboard())
            else:
                await query.edit_message_text("❌ حداقل ۲ تخم مرغ نیاز دارید!", reply_markup=get_back_to_menu_keyboard())

        elif data == "hatch_rooster":
            user_data = db.get_user(user_id)
            if user_data and user_data['eggs'] >= 2:
                db.deduct_eggs(user_id, 2)
                db.add_animal(user_id, 'rooster')
                db.log_event(user_id, 'hatch_rooster',
                             eggs_before=user_data['eggs'], eggs_after=user_data['eggs'] - 2,
                             extra={'animal': 'rooster'})
                await query.edit_message_text("🐓 جوجهکشی موفق! یک خروس اضافه شد.", reply_markup=get_back_to_menu_keyboard())
            else:
                await query.edit_message_text("❌ حداقل ۲ تخممرغ نیاز دارید!", reply_markup=get_back_to_menu_keyboard())

        elif data == "name_animal":
            animals = db.get_user_animals(user_id)
            if animals:
                await query.edit_message_text(
                    "🏷️ حیوانی که میخواهید نامگذاری کنید را انتخاب کنید:",
                    reply_markup=get_animals_list_keyboard(animals)
                )
            else:
                await query.edit_message_text("❌ شما هیچ حیوانی ندارید!", reply_markup=get_back_to_menu_keyboard())

        elif data.startswith("animal_detail_"):
            animal_id = int(data.split("_")[-1])
            animal = db.get_animal(animal_id)
            if animal and animal['user_id'] == user_id:
                emoji = "🐔" if animal['animal_type'] == 'chicken' else "🐓"
                name = animal['name'] or "بینام"
                animal_type_fa = "مرغ" if animal['animal_type'] == 'chicken' else "خروس"
                context.user_data['naming_animal_id'] = animal_id
                await query.edit_message_text(
                    f"{emoji} {animal_type_fa}: {name}\n\n"
                    f"نام جدید را بنویسید (هزینه: {format_number(NAMING_COST)} امتیاز):"
                )
            else:
                await query.edit_message_text("❌ حیوان یافت نشد.", reply_markup=get_back_to_menu_keyboard())

        elif data == "claim_auto_jik":
            user_before = db.get_user(user_id)
            points = db.claim_pending_auto_jik(user_id)
            if points > 0:
                user_after = db.get_user(user_id)
                db.log_event(user_id, 'auto_jik_claim',
                             points_before=user_before['points'], points_after=user_after['points'],
                             extra={'claimed': points})
                # await query.edit_message_text(
                #     f"✅ {format_number(points)} امتیاز Auto Jik Jik دریافت شد!\n"
                #     f"امتیاز کل: {format_number(user_after['points'])}",
                #     reply_markup=get_back_to_menu_keyboard()
                # )
            else:
                await query.edit_message_text("⏳ هنوز امتیازی برای دریافت وجود ندارد.", reply_markup=get_profile_keyboard())

        elif data == "my_eggs":
            user_data = db.get_user(user_id)
            eggs = user_data['eggs'] if user_data else 0
            await query.edit_message_text(
                f"🥚 تعداد تخممرغهای شما: {eggs}",
                reply_markup=get_egg_hatching_keyboard(eggs)
            )

        elif data == "show_animals":
            animals = db.get_user_animals(user_id)
            if animals:
                await query.edit_message_text(
                    f"🐾 *حیوانات شما* ({len(animals)} عدد)\n\nیکی را انتخاب کنید:",
                    parse_mode="Markdown",
                    reply_markup=get_animals_list_keyboard(animals)
                )
            else:
                await query.edit_message_text("🐾 شما هنوز هیچ حیوانی ندارید!", reply_markup=get_back_to_menu_keyboard())
                
    

    else:
        if not update.message:
            return

        # Handle successful payment FIRST — before any other checks
        # Payment messages have no .text so must not fall through to text handlers
        if update.message.successful_payment:
            await handle_successful_payment(update, context)
            return

        if not update.message.text:
            return
        
        text = update.message.text or ""
        normalized = normalize(text)
        if normalized in ["جیک", "جیک جیک", "jik", "jik jik"]:
            user = update.message.from_user
            user_id = user.id
            chat = update.message.chat
            chat_type = chat.type
            chat_id = chat.id
            db.get_or_create_user(user_id, user.username, user.first_name, user.last_name)
            can_use, remaining_secs = db.can_jik_jik(user_id)
            user_data = db.get_user(user_id)
            pts_before = user_data['points'] if user_data else 0
            if can_use:
                db.use_jik_jik(user_id)
                new_points = db.add_points(user_id, 30)
                db.log_event(
                    user_id, 'jik_jik',
                    chat_type=chat_type,
                    chat_id=chat_id,
                    points_before=pts_before,
                    points_after=new_points,
                    extra={'earned': 30}
                )
                await update.message.reply_text(
                    f"✅ *Jik Jik!* +۳۰ امتیاز!\n\n"
                    f"امتیاز شما: {format_number(new_points)}",
                    parse_mode="Markdown"
                )
            else:
                mins = remaining_secs // 60
                secs = remaining_secs % 60
                db.log_event(user_id, 'jik_jik_cooldown',
                            extra={'remaining_secs': remaining_secs})
                await update.message.reply_text(
                    f"⏳ صبر کنید! {mins} دقیقه و {secs} ثانیه تا استفاده بعدی باقی مانده."
                )
            return
        
        if update.message and update.message.text:
            user_id_temp = update.effective_user.id
            animals_owned = db.get_user_animals(user_id_temp)
            if animals_owned:
                msg_norm = normalize(update.message.text.strip())
                for animal in animals_owned:
                    if animal['name'] and normalize(animal['name']) == msg_norm:
                        emoji = "🐔" if animal['animal_type'] == 'chicken' else "🐓"
                        await update.message.reply_text(
                            f"{emoji} سلام صاحب من! من **{animal['name']}** هستم.",
                            parse_mode="Markdown"
                        )
                        return

        # ==================== Private Chat Only Features ====================

        if not _is_private(update):
            return
        

        text = update.message.text.strip()
        user = update.message.from_user
        user_id = user.id
        db.get_or_create_user(user_id, user.username, user.first_name, user.last_name)

        # Log every DM interaction for session analysis
        db.log_event(user_id, 'login', chat_type='private', chat_id=update.message.chat_id,
                     extra={'text': text[:50]})

        # -------- نامگذاری در انتظار --------
        if context.user_data.get('naming_animal_id'):
            animal_id = context.user_data.pop('naming_animal_id')
            animal = db.get_animal(animal_id)
            if animal and animal['user_id'] == user_id:
                user_data = db.get_user(user_id)
                success, remaining = db.deduct_points(user_id, NAMING_COST)
                if success:
                    db.name_animal(animal_id, text)
                    db.record_payment(user_id, 'name_animal', 'naming', 1, 0)
                    db.log_event(user_id, 'name_animal',
                                 points_before=user_data['points'], points_after=remaining,
                                 extra={'animal_id': animal_id, 'name': text, 'cost': NAMING_COST})
                    await update.message.reply_text(
                        f"✅ حیوان شما با نام «{text}» ثبت شد!\nامتیاز باقیمانده: {format_number(remaining)}",
                        reply_markup=main_menu_keyboard()
                    )
                else:
                    await update.message.reply_text(
                        f"❌ امتیاز کافی ندارید! نیاز به {format_number(NAMING_COST)} امتیاز دارید.",
                        reply_markup=main_menu_keyboard()
                    )
            return
        

        elif text in ["پروفایل 👤", "/profile"]:
            user_data = db.get_user(user_id)
            if not user_data:
                await update.message.reply_text("❌ خطا در دریافت پروفایل.")
                return
            pending = db.get_pending_auto_jik(user_id)
            auto_status = "✅ فعال" if user_data['auto_jik_enabled'] else "❌ غیرفعال"
            await update.message.reply_text(
                f"👤 *پروفایل شما*\n\n"
                f"🏆 امتیاز: {format_number(user_data['points'])}\n"
                f"🥚 تخممرغ: {user_data['eggs']}\n"
                f"🐔 مرغ: {user_data['chickens']}\n"
                f"🐓 خروس: {user_data['roosters']}\n"
                f"⚡ Auto Jik Jik: {auto_status}\n"
                f"🎁 امتیاز معلق: {format_number(pending)}",
                parse_mode="Markdown",
                reply_markup=get_profile_keyboard()
            )

        elif text in ["خرید آیتم 🛒", "/buy"]:
            await update.message.reply_text(
                "🛒 *منوی خرید*\n\nیکی از گزینهها را انتخاب کنید:",
                parse_mode="Markdown",
                reply_markup=get_buy_menu_keyboard()
            )

        elif text in ["تخم\u200cمرغ\u200cهای من 🥚", "تخممرغهای من 🥚", "/eggs"]:
            user_data = db.get_user(user_id)
            eggs = user_data['eggs'] if user_data else 0
            await update.message.reply_text(
                f"🥚 *تخممرغهای شما*\n\nتعداد: {eggs}\n\n"
                f"{'برای جوجهکشی به ۲ تخممرغ نیاز دارید.' if eggs < 2 else 'میتوانید جوجهکشی کنید! 🐣'}",
                parse_mode="Markdown",
                reply_markup=get_egg_hatching_keyboard(eggs)
            )

        elif text in ["حیوانات من 🐾", "/animals"]:
            animals = db.get_user_animals(user_id)
            if animals:
                await update.message.reply_text(
                    f"🐾 *حیوانات شما* ({len(animals)} عدد)\n\nیکی را انتخاب کنید:",
                    parse_mode="Markdown",
                    reply_markup=get_animals_list_keyboard(animals)
                )
            else:
                await update.message.reply_text(
                    "🐾 شما هنوز هیچ حیوانی ندارید!\nابتدا تخممرغ بخرید و جوجهکشی کنید.",
                    reply_markup=main_menu_keyboard()
                )

        elif text in ["بازی دوز 🎮"]:
            from tictactoe_handlers import handle_tictactoe_menu
            await handle_tictactoe_menu(update, context)

        elif text in ["راهنما ❓", "/help"]:
            await update.message.reply_text(
                MESSAGES['help'],
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )

        elif text in ["پرداخت 💰", "/pay"]:
            await update.message.reply_text(
                "💰 لطفاً یکی از پکیجها را انتخاب کنید:",
                reply_markup=get_payment_keyboard()
            )
        