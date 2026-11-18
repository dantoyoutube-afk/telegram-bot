"""
Telegram bot "Rose for 12 Stars" (aiogram 3.x) with Flask pinger for Render 24/7
"""
import asyncio
import hashlib
import html
import logging
import os
import secrets
import sqlite3
import time
import uuid
from threading import Thread

from flask import Flask
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    ErrorEvent,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ----------------------------- CONFIG ---------------------------------
BOT_TOKEN = "9169950174:AAER5e6waegpMJNHOwjFqIjM6PTGC2Ksv6k"
ADMIN_ID = 5430662034
CHANNEL_USERNAME = "@Dan1to_stars"  # Канал для перевірки підписки

PRICE_STARS = 12       # price of one attempt
GRID = 5               # 5x5 field
TOTAL = GRID * GRID   # 25 tickets
WIN_CELLS = 7          # winning tickets: 7/25
MAX_TEXT_LEN = 128    # max length of the inscription
DB_PATH = "bot.db"
# -----------------------------------------------------------------------

RNG = secrets.SystemRandom()

# ------------------------------ TEXTS ----------------------------------
T = {
    "en": {
        "choose_lang": "🌍 Choose your language / Оберіть мову / Выберите язык",
        "sub_required": "📢 To use the bot, please subscribe to the channel first!",
        "sub_btn": "📢 Subscribe to channel",
        "sub_check_btn": "✅ I have subscribed",
        "sub_not_yet": "❌ You haven't subscribed to the channel yet. Please subscribe to continue.",
        "offer": (
            "🌹 <b>Rose for {price} ⭐</b>\n\n"
            "Pick 1 ticket out of {total}.\n"
            "🎯 Winning tickets: <b>{wins} of {total}</b>.\n"
            "🔐 The layout is fixed before you pick and can be verified after the game."
        ),
        "pay_btn": "🎲 Go to payment",
        "invoice_title": "Rose 🌹",
        "invoice_desc": "Клікніть нижче щоб оплатити",
        "pick_header": (
            "✅ <b>Payment confirmed</b>\n\n"
            "🎟 Now choose a ticket below 👇\n\n"
            "🎯 Winning: {wins} of {total}\n"
            "🔐 Layout hash:\n<code>{hash}</code>"
        ),
        "lose": (
            "😢 <b>Unfortunately, empty</b>\n\n"
            "You picked an empty ticket ❌\n"
            "Try again!\n\n"
            "🍀 Good luck next time!\n\n"
            "📊 <b>Results:</b>\n"
            "🌹 - winning ticket\n"
            "⬜ - empty ticket\n"
            "❌ - your empty pick"
        ),
        "win": (
            "🎉 <b>Congratulations! You won a rose!</b> 🌹\n\n"
            "You picked a winning ticket 🏆\n\n"
            "📊 <b>Results:</b>\n"
            "🌹 - winning ticket\n"
            "⬜ - empty ticket\n"
            "🏆 - your winning pick\n\n"
            "✍️ You can add an inscription to the gift or submit the request right away."
        ),
        "btn_menu": "⬅️ To game menu",
        "btn_again": "🎲 Play again",
        "btn_add_text": "✍️ Add inscription",
        "btn_submit": "✅ Submit request",
        "ask_text": "✍️ Send the inscription text (up to {n} characters).",
        "too_long": "⚠️ Too long - maximum {n} characters. Try again.",
        "request_sent": "🎉 Withdrawal request submitted",
        "oops": "Oops.. something went wrong, please contact support",
        "already": "This game is already finished.",
        "not_found": "Game not found.",
    },
    "ru": {
        "choose_lang": "🌍 Choose your language / Оберіть мову / Выберите язык",
        "sub_required": "📢 Чтобы пользоваться ботом, подпишитесь на канал!",
        "sub_btn": "📢 Подписаться на канал",
        "sub_check_btn": "✅ Я подписался",
        "sub_not_yet": "❌ Вы еще не подписались на канал. Пожалуйста, подпишитесь, чтобы продолжить.",
        "offer": (
            "🌹 <b>Роза за {price} ⭐</b>\n\n"
            "Выберите 1 билет из {total}.\n"
            "🎯 Выигрышных билетов: <b>{wins} из {total}</b>.\n"
            "🔐 Раскладка фиксируется до вашего выбора, её можно проверить после игры."
        ),
        "pay_btn": "🎲 Перейти к оплате",
        "invoice_title": "Роза 🌹",
        "invoice_desc": "Клікніть нижче щоб оплатити",
        "pick_header": (
            "✅ <b>Подтверждение оплаты</b>\n\n"
            "🎟 Теперь выберите билет ниже 👇\n\n"
            "🎯 Выигрышных: {wins} из {total}\n"
            "🔐 Хеш раскладки:\n<code>{hash}</code>"
        ),
        "lose": (
            "😢 <b>К сожалению, пусто</b>\n\n"
            "Вы выбрали пустой билет ❌\n"
            "Попробуйте ещё раз!\n\n"
            "🍀 Удача улыбнётся вам в следующий раз!\n\n"
            "📊 <b>Результаты:</b>\n"
            "🌹 - выигрышный билет\n"
            "⬜ - пустой билет\n"
            "❌ - ваш пустой выбор"
        ),
        "win": (
            "🎉 <b>Поздравляем! Вы выиграли розу!</b> 🌹\n\n"
            "Вы выбрали выигрышный билет 🏆\n\n"
            "📊 <b>Результаты:</b>\n"
            "🌹 - выигрышный билет\n"
            "⬜ - пустой билет\n"
            "🏆 - ваш выигрышный выбор\n\n"
            "✍️ Можете добавить надпись к подарку или сразу подать заявку."
        ),
        "btn_menu": "⬅️ В меню игры",
        "btn_again": "🎲 Сыграть ещё",
        "btn_add_text": "✍️ Добавить надпись",
        "btn_submit": "✅ Подать заявку",
        "ask_text": "✍️ Отправьте текст надписи (до {n} символов). Попробуйте ещё раз.",
        "too_long": "⚠️ Слишком длинно - максимум {n} символов. Попробуйте ещё раз.",
        "request_sent": "🎉 Заявка на вывод подана",
        "oops": "Упс.. что-то не так",
        "already": "Эта игра уже завершена.",
        "not_found": "Игра не найдена.",
    },
    "uk": {
        "choose_lang": "🌍 Choose your language / Оберіть мову / Выберите язык",
        "sub_required": "📢 Щоб користуватися ботом, підпишіться на канал!",
        "sub_btn": "📢 Підписатися на канал",
        "sub_check_btn": "✅ Я підписався",
        "sub_not_yet": "❌ Ви ще не підписалися на канал. Будь ласка, підпишіться, щоб продовжити.",
        "offer": (
            "🌹 <b>Троянда за {price} ⭐</b>\n\n"
            "Оберіть 1 квиток із {total}.\n"
            "🎯 Виграшних квитків: <b>{wins} із {total}</b>.\n"
            "🔐 Розкладка фіксується до вашого вибору, її можна перевірити після гри."
        ),
        "pay_btn": "🎲 Перейти до оплати",
        "invoice_title": "Троянда 🌹",
        "invoice_desc": "Клікніть нижче щоб оплатити",
        "pick_header": (
            "✅ <b>Підтвердження оплати</b>\n\n"
            "🎟 Тепер оберіть квиток нижче 👇\n\n"
            "🎯 Виграшних: {wins} із {total}\n"
            "🔐 Хеш розкладки:\n<code>{hash}</code>"
        ),
        "lose": (
            "😢 <b>На жаль, пусто</b>\n\n"
            "Ви обрали порожній квиток ❌\n"
            "Спробуйте ще раз!\n\n"
            "🍀 Удача посміхнеться вам наступного разу!\n\n"
            "📊 <b>Результати:</b>\n"
            "🌹 - виграшний квиток\n"
            "⬜ - порожній квиток\n"
            "❌ - ваш порожній вибір"
        ),
        "win": (
            "🎉 <b>Вітаємо! Ви виграли троянду!</b> 🌹\n\n"
            "Ви обрали виграшний квиток 🏆\n\n"
            "📊 <b>Результати:</b>\n"
            "🌹 - виграшний квиток\n"
            "⬜ - порожній квиток\n"
            "🏆 - ваш виграшний вибір\n\n"
            "✍️ Можете додати надпис до подарунка або одразу подати заявку."
        ),
        "btn_menu": "⬅️ В меню гри",
        "btn_again": "🎲 Зіграти ще",
        "btn_add_text": "✍️ Додати надпис",
        "btn_submit": "✅ Подати заявку",
        "ask_text": "✍️ Надішліть текст надпису (до {n} символів).",
        "too_long": "⚠️ Занадто довго - максимум {n} символів. Спробуйте ще раз.",
        "request_sent": "🎉 Заявка на вивід подана",
        "oops": "Упс.. щось пішло не так",
        "already": "Ця гра вже завершена.",
        "not_found": "Гру не знайдено.",
    },
}

# ------------------------------ DATABASE -------------------------------
db = sqlite3.connect(DB_PATH, isolation_level=None, check_same_thread=False)
db.row_factory = sqlite3.Row
db.executescript(
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        lang TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS games (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        grid TEXT NOT NULL,
        salt TEXT NOT NULL,
        commit_hash TEXT NOT NULL,
        charge_id TEXT UNIQUE,
        status TEXT NOT NULL,      -- paid / lost / won / claiming / claimed
        picked INTEGER,
        inscription TEXT,
        created INTEGER NOT NULL
    );
    """
)

pending_text: dict[int, tuple[str, int]] = {}

router = Router()
router.message.filter(F.chat.type == "private")

# ------------------------------ FLASK PINGER ---------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
# -----------------------------------------------------------------------


def get_lang(user_id: int) -> str:
    row = db.execute("SELECT lang FROM users WHERE user_id=?", (user_id,)).fetchone()
    return row["lang"] if row else "en"


def tr(user_id: int, key: str, **kw) -> str:
    return T[get_lang(user_id)][key].format(**kw)


def get_game(game_id: str, user_id: int):
    return db.execute(
        "SELECT * FROM games WHERE id=? AND user_id=?", (game_id, user_id)
    ).fetchone()


async def check_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            return True
    except Exception:
        pass
    return False


# ----------------------------- KEYBOARDS -------------------------------
def sub_kb(user_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=tr(user_id, "sub_btn"), url="https://t.me/Dan1to_stars")
    b.button(text=tr(user_id, "sub_check_btn"), callback_data="check_sub")
    b.adjust(1)
    return b.as_markup()


def build_grid_kb(game_id: str, grid: str | None = None, picked: int | None = None,
                  extras: list[tuple[str, str]] | None = None) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for i in range(TOTAL):
        if grid is None:
            b.button(text="⬜", callback_data=f"pick:{game_id}:{i}")
        else:
            win = grid[i] == "1"
            if i == picked:
                text = "🏆" if win else "❌"
            else:
                text = "🌹" if win else "⬜"
            b.button(text=text, callback_data="noop")
    extras = extras or []
    for text, cb in extras:
        b.button(text=text, callback_data=cb)
    b.adjust(*([GRID] * GRID + [1] * len(extras)))
    return b.as_markup()


def offer_text(user_id: int) -> str:
    return tr(user_id, "offer", price=PRICE_STARS, total=TOTAL, wins=WIN_CELLS)


def offer_kb(user_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=tr(user_id, "pay_btn"), callback_data="pay")
    return b.as_markup()


# ------------------------------ HANDLERS -------------------------------
@router.message(CommandStart())
@router.message(Command("lang"))
async def cmd_start(m: Message):
    b = InlineKeyboardBuilder()
    b.button(text="🇬🇧 English", callback_data="lang:en")
    b.button(text="🇷🇺 Русский", callback_data="lang:ru")
    b.button(text="🇺🇦 Українська", callback_data="lang:uk")
    b.adjust(1)
    await m.answer(T["en"]["choose_lang"], reply_markup=b.as_markup())


@router.callback_query(F.data.startswith("lang:"))
async def set_lang(c: CallbackQuery, bot: Bot):
    lang = c.data.split(":")[1]
    if lang not in T:
        lang = "en"
    user_id = c.from_user.id
    db.execute(
        "INSERT INTO users(user_id, lang) VALUES(?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang",
        (user_id, lang),
    )
    await c.answer()

    if not await check_subscription(bot, user_id):
        await c.message.edit_text(tr(user_id, "sub_required"), reply_markup=sub_kb(user_id))
    else:
        await c.message.edit_text(offer_text(user_id), reply_markup=offer_kb(user_id))


@router.callback_query(F.data == "check_sub")
async def check_sub_callback(c: CallbackQuery, bot: Bot):
    user_id = c.from_user.id
    if await check_subscription(bot, user_id):
        await c.answer()
        await c.message.edit_text(offer_text(user_id), reply_markup=offer_kb(user_id))
    else:
        await c.answer(tr(user_id, "sub_not_yet"), show_alert=True)


@router.callback_query(F.data == "menu")
async def menu(c: CallbackQuery, bot: Bot):
    user_id = c.from_user.id
    await c.answer()
    if not await check_subscription(bot, user_id):
        await c.message.answer(tr(user_id, "sub_required"), reply_markup=sub_kb(user_id))
    else:
        await c.message.answer(offer_text(user_id), reply_markup=offer_kb(user_id))


async def send_invoice(bot: Bot, chat_id: int, user_id: int):
    title = tr(user_id, "invoice_title")
    await bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=tr(user_id, "invoice_desc"),
        payload=f"rose:{user_id}:{uuid.uuid4().hex[:8]}",
        provider_token="",          # must be empty for Telegram Stars
        currency="XTR",
        prices=[LabeledPrice(label=title, amount=PRICE_STARS)],
    )


@router.callback_query(F.data.in_({"pay", "again"}))
async def pay(c: CallbackQuery, bot: Bot):
    user_id = c.from_user.id
    await c.answer()
    if not await check_subscription(bot, user_id):
        await c.message.answer(tr(user_id, "sub_required"), reply_markup=sub_kb(user_id))
        return
    await send_invoice(bot, c.message.chat.id, user_id)


@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await q.answer(ok=True)


@router.message(F.successful_payment)
async def paid(m: Message, bot: Bot):
    sp = m.successful_payment
    user_id = m.from_user.id

    if db.execute("SELECT 1 FROM games WHERE charge_id=?", (sp.telegram_payment_charge_id,)).fetchone():
        return

    try:
        winners = set(RNG.sample(range(TOTAL), WIN_CELLS))
        grid = "".join("1" if i in winners else "0" for i in range(TOTAL))
        salt = secrets.token_hex(16)
        commit = hashlib.sha256(f"{salt}:{grid}".encode()).hexdigest()
        game_id = secrets.token_hex(6)
        db.execute(
            "INSERT INTO games(id, user_id, grid, salt, commit_hash, charge_id, status, created) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (game_id, user_id, grid, salt, commit, sp.telegram_payment_charge_id, "paid", int(time.time())),
        )
        await m.answer(
            tr(user_id, "pick_header", wins=WIN_CELLS, total=TOTAL, hash=commit),
            reply_markup=build_grid_kb(game_id),
        )
    except Exception:
        logging.exception("Failure after payment, refunding")
        try:
            await bot.refund_star_payment(
                user_id=user_id,
                telegram_payment_charge_id=sp.telegram_payment_charge_id,
            )
        except Exception:
            logging.exception("Refund failed")
        await m.answer(tr(user_id, "oops"))


@router.callback_query(F.data == "noop")
async def noop(c: CallbackQuery):
    await c.answer()


@router.callback_query(F.data.startswith("pick:"))
async def pick(c: CallbackQuery, bot: Bot):
    user_id = c.from_user.id
    if not await check_subscription(bot, user_id):
        await c.answer(tr(user_id, "sub_not_yet"), show_alert=True)
        return

    _, game_id, idx_s = c.data.split(":")
    idx = int(idx_s)

    g = get_game(game_id, user_id)
    if not g or not 0 <= idx < TOTAL:
        await c.answer(tr(user_id, "not_found"), show_alert=True)
        return

    won = g["grid"][idx] == "1"
    cur = db.execute(
        "UPDATE games SET status=?, picked=? WHERE id=? AND status='paid'",
        ("won" if won else "lost", idx, game_id),
    )
    if cur.rowcount == 0:
        await c.answer(tr(user_id, "already"), show_alert=True)
        return

    if won:
        text = tr(user_id, "win")
        extras = [
            (tr(user_id, "btn_add_text"), f"txt:{game_id}"),
            (tr(user_id, "btn_submit"), f"send:{game_id}"),
        ]
    else:
        text = tr(user_id, "lose")
        extras = [
            (tr(user_id, "btn_menu"), "menu"),
            (tr(user_id, "btn_again"), "again"),
        ]
    await c.answer()
    await c.message.edit_text(text, reply_markup=build_grid_kb(game_id, g["grid"], idx, extras))


@router.callback_query(F.data.startswith("txt:"))
async def ask_text(c: CallbackQuery):
    user_id = c.from_user.id
    game_id = c.data.split(":")[1]
    g = get_game(game_id, user_id)
    if not g or g["status"] != "won":
        await c.answer(tr(user_id, "already"), show_alert=True)
        return
    pending_text[user_id] = (game_id, c.message.message_id)
    await c.answer()
    await c.message.answer(tr(user_id, "ask_text", n=MAX_TEXT_LEN))


@router.callback_query(F.data.startswith("send:"))
async def send_without_text(c: CallbackQuery, bot: Bot):
    game_id = c.data.split(":")[1]
    await c.answer()
    await claim(bot, c.from_user, c.message.chat.id, c.message.message_id, game_id, None)


@router.message(F.text & ~F.text.startswith("/"))
async def got_text(m: Message, bot: Bot):
    user_id = m.from_user.id
    pending = pending_text.get(user_id)
    if not pending:
        return
    text = m.text.strip()
    if len(text) > MAX_TEXT_LEN:
        await m.answer(tr(user_id, "too_long", n=MAX_TEXT_LEN))
        return
    game_id, message_id = pending
    await claim(bot, m.from_user, m.chat.id, message_id, game_id, text)


def user_link(user) -> str:
    if user.username:
        return f"@{user.username}"
    name = html.escape(user.full_name or "user")
    return f'<a href="tg://user?id={user.id}">{name}</a>'


async def claim(bot: Bot, user, chat_id: int, message_id: int, game_id: str, inscription: str | None):
    g = get_game(game_id, user.id)
    if not g:
        await bot.send_message(chat_id, tr(user.id, "not_found"))
        return

    cur = db.execute(
        "UPDATE games SET status='claiming', inscription=? WHERE id=? AND status='won'",
        (inscription, game_id),
    )
    if cur.rowcount == 0:
        await bot.send_message(chat_id, tr(user.id, "already"))
        return

    admin_text = (
        "🌹 <b>New winner!</b>\n\n"
        f"👤 {user_link(user)}\n"
        f"🆔 <code>{user.id}</code>\n"
        f"🎮 <code>{game_id}</code>"
    )
    if inscription:
        admin_text += f"\n\n✍️ Inscription:\n<code>{html.escape(inscription)}</code>"

    try:
        await bot.send_message(ADMIN_ID, admin_text)
    except Exception:
        logging.exception("Cannot notify admin")
        db.execute("UPDATE games SET status='won' WHERE id=?", (game_id,))
        await bot.send_message(chat_id, tr(user.id, "oops"))
        return

    db.execute("UPDATE games SET status='claimed' WHERE id=?", (game_id,))
    pending_text.pop(user.id, None)

    try:
        await bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=build_grid_kb(
                game_id, g["grid"], g["picked"],
                [(tr(user.id, "btn_menu"), "menu"), (tr(user.id, "btn_again"), "again")],
            ),
        )
    except Exception:
        logging.exception("Cannot update keyboard")
    await bot.send_message(chat_id, tr(user.id, "request_sent"))


@router.error()
async def on_error(event: ErrorEvent, bot: Bot):
    logging.exception("Unhandled error", exc_info=event.exception)
    upd = event.update
    chat_id = user_id = None
    if upd.message:
        chat_id, user_id = upd.message.chat.id, upd.message.from_user.id
    elif upd.callback_query:
        user_id = upd.callback_query.from_user.id
        chat_id = upd.callback_query.message.chat.id if upd.callback_query.message else user_id
    if chat_id:
        try:
            await bot.send_message(chat_id, tr(user_id, "oops"))
        except Exception:
            pass


async def main():
    logging.basicConfig(level=logging.INFO)
    if not BOT_TOKEN or not ADMIN_ID:
        raise SystemExit("Set configuration!")
    
    # Запускаємо Flask у фоновому потоці для обходу вимкнення на Render
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
    
