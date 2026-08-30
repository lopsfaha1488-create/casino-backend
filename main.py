import logging
import random
import uuid
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# =========================================================
# ⚙️ НАСТРОЙКИ И РЕКВИЗИТЫ
# =========================================================

TOKEN = "8733911430:AAF0y4vZM-E1JoiS9PkgHSF8aBE5BcZsfzY"
ADMIN_ID = 8507520917

CARD_NUMBER = "2200396113165076"
CRYPTO_ADDRESS = "TTPjHC9vAyGX9FLjQ8F9BjCvTCwr2Q1ZLT"

# ТВОЯ ССЫЛКА НА МИНИ-ПРИЛОЖЕНИЕ
WEBAPP_URL = "https://lopsfaha1488-create.github.io/casino-limbo/"

# =========================================================
# СЕРВИСНЫЕ НАСТРОЙКИ
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

user_balances = {}
user_cards = {}
pending_deposits = {}
withdraw_requests = {}

def get_balance(user_id: int) -> int:
    return user_balances.get(user_id, 0)

def update_balance(user_id: int, amount: int):
    user_balances[user_id] = get_balance(user_id) + amount

def generate_order_id() -> str:
    return uuid.uuid4().hex[:8].upper()

def mask_card(card: str) -> str:
    if card and len(card) == 16:
        return f"{card[:4]} **** "
    return "Не привязана"

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎰 Играть в казино", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("💰 Баланс", callback_data="balance"),
         InlineKeyboardButton("💳 Пополнить", callback_data="deposit")],
        [InlineKeyboardButton("📤 Вывести", callback_data="withdraw"),
         InlineKeyboardButton("📞 Поддержка", callback_data="support")]
    ]
    return InlineKeyboardMarkup(keyboard)

# =========================================================
# 🏠 ГЛАВНОЕ МЕНЮ
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data.clear()
    
    text = (
        f"✨ ⚡️ <b>WELCOME TO CASINO LIMBO</b> ⚡️ ✨\n\n"
        f"💰 <b>Ваш баланс:</b> <code>{get_balance(user_id)} ₽</code>\n"
        f"💳 <b>Карта:</b> <code>{mask_card(user_cards.get(user_id))}</code>\n\n"
        "Нажмите кнопку ниже, чтобы открыть казино и начать играть! 👇"
    )
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=get_main_keyboard())

# =========================================================
# 💳 ПОПОЛНЕНИЕ И ВЫВОД
# =========================================================

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    await query.edit_message_text(
        f"💎 <b>ВАШ БАЛАНС</b>\n\n"
        f"💵 Доступно: <code>{get_balance(user_id)} ₽</code>\n"
        f"💳 Карта: <code>{mask_card(user_cards.get(user_id))}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]])
    )

async def deposit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in user_cards:
        context.user_data["state"] = "WAITING_CARD_DEPOSIT"
        await query.edit_message_text(
            "💳 <b>Привязка банковской карты</b>\n\n"
            "Введите 16-значный номер карты для депозитов и выплат:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="back_to_menu")]])
        )
        return

    keyboard = [
        [InlineKeyboardButton("💳 Карта банка", callback_data="pay_card")],
        [InlineKeyboardButton("🪙 Криптовалюта (USDT)", callback_data="pay_crypto")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    await query.edit_message_text(
        f"💳 <b>Пополнение счета</b>\n"
        f"Привязано: <code>{mask_card(user_cards[user_id])}</code>\n\n"
        f"Выберите способ оплаты:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def deposit_select_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data.split("_")[1]
    
    context.user_data["deposit_method"] = method
    context.user_data["state"] = "WAITING_DEPOSIT_AMOUNT"

    await query.edit_message_text(
        "💵 <b>Сумма пополнения</b>\n\n"
        "Введите желаемую сумму депозита в чат:\n"
        "<i>Минимально: 500 ₽ | Максимально: 10 000 ₽</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="back_to_menu")]])
    )

async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in user_cards:
        context.user_data["state"] = "WAITING_CARD_DEPOSIT"
        await query.edit_message_text(
            "❌ <b>Карта не привязана!</b>\nВведите 16-значный номер карты:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]])
        )
        return

    context.user_data["state"] = "WAITING_WITHDRAW_AMOUNT"
    await query.edit_message_text(
        f"📤 <b>Вывод средств</b>\n"
        f"На карту: <code>{mask_card(user_cards[user_id])}</code>\n\n"
        f"Доступно: <code>{get_balance(user_id)} ₽</code>\n"
        "Введите сумму вывода (от 500 ₽):",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="back_to_menu")]])
    )

# =========================================================
# 📞 ПОДДЕРЖКА
# =========================================================

async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["state"] = "WAITING_SUPPORT_MSG"
    
    await query.edit_message_text(
        "📞 <b>Служба поддержки</b>\n\n"
        "Задайте свой вопрос или опишите проблему прямо в сообщении чата.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="back_to_menu")]])
    )

async def admin_reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    target_user_id = int(query.data.split(":")[1])
    
    context.user_data["state"] = "WAITING_ADMIN_REPLY_TEXT"
    context.user_data["reply_target"] = target_user_id
    
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"✍️ <b>Введите текст ответа для пользователя</b> <code>{target_user_id}</code>:",
        parse_mode="HTML"
    )

# =========================================================
# 📩 ОБРАБОТКА ВВОДА И ТЕКСТА
# =========================================================

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if state == "WAITING_CARD_DEPOSIT":
        card_clean = text.replace(" ", "")
        if not card_clean.isdigit() or len(card_clean) != 16:
            await update.message.reply_text("❌ Номер карты должен состоять из 16 цифр. Попробуйте еще раз:")
            return
        
        user_cards[user_id] = card_clean
        context.user_data.pop("state", None)
        await update.message.reply_text(
            f"✅ Карта <code>{mask_card(card_clean)}</code> привязана!",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )

    elif state == "WAITING_DEPOSIT_AMOUNT":
        if not text.isdigit():
            await update.message.reply_text("❌ Введите корректное число.")
            return

        amount = int(text)
        if amount < 500 or amount > 10000:
            await update.message.reply_text("❌ Сумма должна быть в диапазоне от 500 ₽ до 10 000 ₽:")
            return

        method = context.user_data.get("deposit_method", "card")
        order_id = generate_order_id()
        pending_deposits[user_id] = {"order_id": order_id, "method": method, "amount": amount}
        
        context.user_data["state"] = "WAITING_RECEIPT"
        details = f"<code>{CARD_NUMBER}</code>" if method == "card" else f"<code>{CRYPTO_ADDRESS}</code>"

        admin_kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Зачислить", callback_data=f"adm_dep_confirm:{order_id}:{user_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"adm_dep_reject:{order_id}:{user_id}")
            ]
        ])

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 <b>ДЕПОЗИТ ({method.upper()})</b>\n\n"
                 f"👤 Юзер: @{update.effective_user.username or 'без username'}\n"
                 f"🆔 ID: <code>{user_id}</code>\n"
                 f"💰 Сумма: <b>{amount} ₽</b>\n"
                 f"🆔 Заявка: <code>{order_id}</code>",
            parse_mode="HTML",
            reply_markup=admin_kb
        )

        await update.message.reply_text(
            f"💳 <b>Оплата по реквизитам</b>\n\n"
            f"Переведите <b>{amount} ₽</b> на реквизиты:\n{details}\n\n"
            f"🆔 Заявка: <code>{order_id}</code>\n\n"
            f"⚠️ <b>После оплаты пришлите скриншот чека в этот чат!</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="back_to_menu")]])
        )

    elif state == "WAITING_WITHDRAW_AMOUNT":
        if not text.isdigit():
            await update.message.reply_text("❌ Введите сумму числом.")
            return

        amount = int(text)
        if amount < 500:
            await update.message.reply_text("❌ Минимальная сумма вывода — 500 ₽.")
            return

        if get_balance(user_id) < amount:
            await update.message.reply_text("❌ Недостаточно средств на балансе.")
            return

        order_id = generate_order_id()
        withdraw_requests[order_id] = {"user_id": user_id, "amount": amount}
        context.user_data.pop("state", None)

        admin_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Подтвердить", callback_data=f"adm_w_confirm:{order_id}"),
             InlineKeyboardButton("❌ Отклонить", callback_data=f"adm_w_reject:{order_id}")]
        ])

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📤 <b>ЗАЯВКА НА ВЫВОД</b>\n\n"
                 f"👤 Юзер: @{update.effective_user.username or 'без username'}\n"
                 f"🆔 ID: <code>{user_id}</code>\n"
                 f"💰 Сумма: <b>{amount} ₽</b>\n"
                 f"💳 Карта: <code>{user_cards[user_id]}</code>",
            parse_mode="HTML",
            reply_markup=admin_kb
        )

        await update.message.reply_text(
            f"✅ <b>Заявка на вывод создана!</b>\n🆔 ID: <code>{order_id}</code>\nОжидайте обработки оператором.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )

    elif state == "WAITING_SUPPORT_MSG":
        context.user_data.pop("state", None)
        admin_kb = InlineKeyboardMarkup([[InlineKeyboardButton("💬 Ответить", callback_data=f"reply_sup:{user_id}")]])
        
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📩 <b>ОБРАЩЕНИЕ В ПОДДЕРЖКУ</b>\n\n"
                 f"👤 От: @{update.effective_user.username or 'без username'}\n"
                 f"🆔 ID: <code>{user_id}</code>\n\n"
                 f"💬 <b>Текст:</b>\n{text}",
            parse_mode="HTML",
            reply_markup=admin_kb
        )
        
        await update.message.reply_text(
            "✅ <b>Сообщение отправлено поддержки!</b>\nВам ответят в ближайшее время.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )

    elif state == "WAITING_ADMIN_REPLY_TEXT" and user_id == ADMIN_ID:
        target_user = context.user_data.get("reply_target")
        context.user_data.pop("state", None)
        context.user_data.pop("reply_target", None)

        if target_user:
            try:
                await context.bot.send_message(
                    chat_id=target_user,
                    text=f"👨‍💻 <b>Ответ службы поддержки:</b>\n\n{text}",
                    parse_mode="HTML"
                )
                await update.message.reply_text(f"✅ Доставлено пользователю <code>{target_user}</code>!", parse_mode="HTML")
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка отправки: {e}")

    elif state == "WAITING_ADMIN_DEP_AMOUNT" and user_id == ADMIN_ID:
        if not text.isdigit():
            await update.message.reply_text("❌ Введите число.")
            return

        amount = int(text)
        target_id = context.user_data.get("deposit_target")
        
        if target_id:
            update_balance(target_id, amount)
            await update.message.reply_text(f"✅ Баланс <code>{target_id}</code> успешно пополнен на <b>{amount} ₽</b>", parse_mode="HTML")
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"🎉 <b>Депозит подтвержден!</b>\nЗачислено: <b>{amount} ₽</b>",
                    parse_mode="HTML"
                )
            except Exception:
                pass

        context.user_data.pop("state", None)
        context.user_data.pop("deposit_target", None)

    else:
        await update.message.reply_text("Используйте меню управления.")

async def handle_media_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if context.user_data.get("state") != "WAITING_RECEIPT" or user_id not in pending_deposits:
        await update.message.reply_text("❌ Нет активных запросов на подтверждение пополнения.")
        return

    dep_info = pending_deposits.pop(user_id)
    order_id = dep_info["order_id"]
    amount = dep_info.get("amount", 0)
    context.user_data.pop("state", None)

    caption = (
        f"🧾 <b>ЧЕК К ЗАЯВКЕ #{order_id}</b>\n"
        f"👤 От: @{update.effective_user.username or 'без username'}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"💰 Заявка: <b>{amount} ₽</b>"
    )

    admin_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Зачислить", callback_data=f"adm_dep_confirm:{order_id}:{user_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"adm_dep_reject:{order_id}:{user_id}")
        ]
    ])

    if update.message.photo:
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, caption=caption, parse_mode="HTML", reply_markup=admin_kb)
    elif update.message.document:
        await context.bot.send_document(chat_id=ADMIN_ID, document=update.message.document.file_id, caption=caption, parse_mode="HTML", reply_markup=admin_kb)

    await update.message.reply_text(
        "⏳ <b>Чек успешно принят на проверку!</b>\nОжидайте зачисления средств.",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

# =========================================================
# ⚙️ АДМИНИСТРИРОВАНИЕ
# =========================================================

async def admin_deposit_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("Доступ запрещен", show_alert=True)
        return

    _, order_id, target_user_id = query.data.split(":")
    target_user_id = int(target_user_id)

    if query.data.startswith("adm_dep_reject"):
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"❌ <b>Ваша заявка #{order_id} была отклонена.</b>",
                parse_mode="HTML"
            )
        except Exception:
            pass

        msg_text = f"{query.message.caption or query.message.text}\n\n❌ <b>ОТКЛОНЕНО</b>"
        if query.message.photo or query.message.document:
            await query.edit_message_caption(caption=msg_text, parse_mode="HTML", reply_markup=None)
        else:
            await query.edit_message_text(text=msg_text, parse_mode="HTML", reply_markup=None)
        
        await query.answer("Отклонено")

    elif query.data.startswith("adm_dep_confirm"):
        context.user_data["deposit_target"] = target_user_id
        context.user_data["state"] = "WAITING_ADMIN_DEP_AMOUNT"
        
        await query.answer()
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"💰 Введите сумму зачисления для пользователя <code>{target_user_id}</code>:",
            parse_mode="HTML"
        )

async def admin_withdraw_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("Доступ запрещен", show_alert=True)
        return

    action, order_id = query.data.split(":")
    req = withdraw_requests.get(order_id)
    
    if not req:
        await query.answer("Заявка не найдена!", show_alert=True)
        return

    user_id = req["user_id"]
    amount = req["amount"]

    if action == "adm_w_confirm":
        if get_balance(user_id) >= amount:
            update_balance(user_id, -amount)
            await context.bot.send_message(user_id, f"✅ Вывод <b>{amount} ₽</b> успешно подтвержден!", parse_mode="HTML")
            await query.edit_message_text(f"✅ Вывод #{order_id} на {amount} ₽ ПОДТВЕРЖДЕН.")
        else:
            await query.answer("Недостаточно средств у пользователя!", show_alert=True)
    else:
        await context.bot.send_message(user_id, f"❌ Заявка на вывод <b>{amount} ₽</b> отклонена.", parse_mode="HTML")
        await query.edit_message_text(f"❌ Вывод #{order_id} ОТКЛОНЕН.")
    
    withdraw_requests.pop(order_id, None)

async def admin_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
        update_balance(target_id, amount)
        
        await update.message.reply_text(f"✅ Баланс {target_id}: {get_balance(target_id)} ₽")
        await context.bot.send_message(target_id, f"💳 <b>Ваш баланс пополнен на {amount} ₽!</b>", parse_mode="HTML")
    except Exception:
        await update.message.reply_text("Команда: `/addbalance ID СУММА`", parse_mode="Markdown")

# =========================================================
# 🚀 ЗАПУСК
# =========================================================

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addbalance", admin_add_balance))

    app.add_handler(CallbackQueryHandler(start, pattern="^back_to_menu$"))
    app.add_handler(CallbackQueryHandler(show_balance, pattern="^balance$"))
    app.add_handler(CallbackQueryHandler(deposit_start, pattern="^deposit$"))
    app.add_handler(CallbackQueryHandler(deposit_select_method, pattern="^pay_"))
    app.add_handler(CallbackQueryHandler(withdraw_start, pattern="^withdraw$"))
    app.add_handler(CallbackQueryHandler(support_start, pattern="^support$"))

    app.add_handler(CallbackQueryHandler(admin_reply_start, pattern="^reply_sup:"))

    app.add_handler(CallbackQueryHandler(admin_withdraw_action, pattern="^adm_w_"))
    app.add_handler(CallbackQueryHandler(admin_deposit_action, pattern="^adm_dep_"))

    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_media_receipt))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))

    print("=================================")
    print("🎰 CASINO LIMBO БОТ ЗАПУЩЕН!")
    print("📱 МИНИ-ПРИЛОЖЕНИЕ ПОДКЛЮЧЕНО!")
    print("=================================")

    app.run_polling()

if __name__ == "__main__":
    main()