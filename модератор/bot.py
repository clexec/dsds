import asyncio
import json
import os
import logging
import re
import time
from datetime import datetime, timedelta, date
from typing import Optional

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatMemberStatus
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ChatPermissions, ChatMemberUpdated, FSInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ─── FSM States ──────────────────────────────────────────────────────────────
class BroadcastFSM(StatesGroup):
    waiting_text = State()

class CensorFSM(StatesGroup):
    waiting_words = State()

class RulesFSM(StatesGroup):
    waiting_text = State()

BOT_TOKEN = "8375872283:AAFjMtiel1z6-5KZ62f5l1IptmxAXjHTOrk"
LOG_BOT_TOKEN = "8204350438:AAH4LLSiuiH2NjefS5hYFYsvpvwcvwEoD9U"
OWNER_ID = 8249995740
OWNER_USERNAME = "seyats"
CHANNEL = "@seyxts"
DB_FILE = "db.json"
WELCOME_GIF = "emoji.mp4"
WELCOME_GIF_ID: str | None = None

_log_bot: "Bot | None" = None


E = {
    "settings":     '<tg-emoji emoji-id="5278602437001767574">⚙</tg-emoji>',
    "profile":      '<tg-emoji emoji-id="5275979556308674886">👤</tg-emoji>',
    "people":       '<tg-emoji emoji-id="5298668674532538341">👥</tg-emoji>',
    "check":        '<tg-emoji emoji-id="5278411813468269386">✅</tg-emoji>',
    "cross":        '<tg-emoji emoji-id="5278578973595427038">❌</tg-emoji>',
    "pencil":       '<tg-emoji emoji-id="5276442772826515132">✍</tg-emoji>',
    "trash":        '<tg-emoji emoji-id="5276384644739129761">🗑</tg-emoji>',
    "link":         '<tg-emoji emoji-id="5278305362703835500">🔗</tg-emoji>',
    "info":         '<tg-emoji emoji-id="5278753302023004775">ℹ</tg-emoji>',
    "bot":          '<tg-emoji emoji-id="5276127848644503161">🤖</tg-emoji>',
    "eye":          '<tg-emoji emoji-id="5276395476646653290">👁</tg-emoji>',
    "bell":         '<tg-emoji emoji-id="5206222720416643915">🔔</tg-emoji>',
    "gift":         '<tg-emoji emoji-id="5276422526350681413">🎁</tg-emoji>',
    "clock":        '<tg-emoji emoji-id="5276412364458059956">⏰</tg-emoji>',
    "party":        '<tg-emoji emoji-id="5278611606756942667">🎉</tg-emoji>',
    "star":         '<tg-emoji emoji-id="5276111746812112286">⭐</tg-emoji>',
    "shield":       '<tg-emoji emoji-id="5276262671962892944">🛡</tg-emoji>',
    "warn":         '<tg-emoji emoji-id="5276240711795107620">⚠</tg-emoji>',
    "pc":           '<tg-emoji emoji-id="5278647306525108244">🖥</tg-emoji>',
    "crown":        '<tg-emoji emoji-id="5276229330131772747">👑</tg-emoji>',
    "back":         '<tg-emoji emoji-id="5206401524200145033">◁</tg-emoji>',
    "chart":        '<tg-emoji emoji-id="5278778882848220741">📊</tg-emoji>',
    "lock":         '<tg-emoji emoji-id="5278602437001767574">🔒</tg-emoji>',
    "unlock":       '<tg-emoji emoji-id="5278602437001767574">🔓</tg-emoji>',
    "mega":         '<tg-emoji emoji-id="5278528159837348960">📣</tg-emoji>',
    "box":          '<tg-emoji emoji-id="5278540791336165644">📦</tg-emoji>',
    "reload":       '<tg-emoji emoji-id="5278611606756942667">🔄</tg-emoji>',
    "home":         '<tg-emoji emoji-id="5278413853577734640">🏘</tg-emoji>',
    "smile":        '<tg-emoji emoji-id="5278611606756942667">🙂</tg-emoji>',
    "book":         '<tg-emoji emoji-id="5206626000665868017">📚</tg-emoji>',
    "code":         '<tg-emoji emoji-id="5276314275994954605">🔨</tg-emoji>',
    "money":        '<tg-emoji emoji-id="5193179982775476271">🪙</tg-emoji>',
    "send":         '<tg-emoji emoji-id="5206401524200145033">⬆</tg-emoji>',
    "down":         '<tg-emoji emoji-id="5206510891247371052">⬇</tg-emoji>',
    "plus":         '<tg-emoji emoji-id="5242329690135356589">➕</tg-emoji>',
    "minus":        '<tg-emoji emoji-id="5244796895443838315">➖</tg-emoji>',
    "excl":         '<tg-emoji emoji-id="5242578970037218790">❕</tg-emoji>',
    "question":     '<tg-emoji emoji-id="5242205011529719330">❔</tg-emoji>',
    "brush":        '<tg-emoji emoji-id="5276442772826515132">🖌</tg-emoji>',
    "bag":          '<tg-emoji emoji-id="5276037216244624892">💼</tg-emoji>',
    "compass":      '<tg-emoji emoji-id="5206202791768393003">🧭</tg-emoji>',
    "gamepad":      '<tg-emoji emoji-id="5278304890257436355">🎮</tg-emoji>',
    "letter":       '<tg-emoji emoji-id="5278589204207528856">📨</tg-emoji>',
    "photo":        '<tg-emoji emoji-id="5278647306525108244">🖼</tg-emoji>',
    "pin":          '<tg-emoji emoji-id="5278305362703835500">📍</tg-emoji>',
    "wallet":       '<tg-emoji emoji-id="5276398496008663230">👛</tg-emoji>',
    "tag":          '<tg-emoji emoji-id="5276422526350681413">🏷</tg-emoji>',
    "heart":        '<tg-emoji emoji-id="5278611606756942667">❤</tg-emoji>',
}

def eb(text: str, emoji_id: str) -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{text}</tg-emoji>'

logging.basicConfig(level=logging.INFO)

def load_db() -> dict:
    if not os.path.exists(DB_FILE):
        return {
            "groups": {},
            "users": {},
            "global_bans": {},
            "approved_owners": [],
            "warned_owners": {},
            "pending_approval": []
        }
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data: dict):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_group(db: dict, chat_id: int) -> dict:
    key = str(chat_id)
    if key not in db["groups"]:
        db["groups"][key] = {
            "rules": "1. Без спама и флуда.\n2. Без рекламы и самопиара.\n3. Без оскорблений и срачей.\n4. Не обсуждаем скам и разводы.\n5. Политика и негативные новости — мимо.\n6. Без угроз и доксинга.\n7. Без наркотиков и суицидального контента.\n8. Без нацизма и разжигания ненависти.\n9. Не кидайте ботов и AI-ботов.\n10. Ведите себя нормально и уважайте других.",
            "staff": {"admins": [], "senior_admins": [], "mods": []},
            "stats_today": {},
            "stats_all": {},
            "stats_date": str(date.today()),
            "total_messages": 0,
            "owner_id": None,
            "rep_triggers_plus": ["+", "++", "+1", "+реп", "+ реп", "уважение", "красава", "огонь", "топ", "молодец", "красавчик", "спасибо", "благодарю", "лайк", "класс", "супер", "респект", "gg"],
            "rep_triggers_minus": ["-", "--", "-1", "-реп", "- реп", "диз", "-диз", "- диз", "бред", "дизлайк", "дно", "зашквар", "кринж", "минус", "мусор", "отстой", "плохо", "позор", "рофл", "слабо", "трэш", "ужас", "фу", "хлам", "чушь"],
            "rep_daily_limit": 5,
            "rep_cooldown_hours": 0.0,
            "rep_titles": [],
            "settings": {
                "welcome": True,
                "antiflood": False,
                "antilinks": False,
                "captcha": False,
                "antispam": False
            },
            "censorship": []
        }
    g = db["groups"][key]
    if "rep_titles" not in g:
        g["rep_titles"] = []
    if "total_messages" not in g:
        g["total_messages"] = 0
    if "censorship" not in g:
        g["censorship"] = []
    if "owner_id" not in g:
        g["owner_id"] = None
    if "antispam" not in g.get("settings", {}):
        g.setdefault("settings", {})["antispam"] = False
    return g

def get_user(db: dict, user_id: int, chat_id: int) -> dict:
    key = f"{chat_id}_{user_id}"
    if key not in db["users"]:
        db["users"][key] = {
            "user_id": user_id,
            "chat_id": chat_id,
            "reputation": 0,
            "warns": 0,
            "violations": 0,
            "muted_until": None,
            "banned": False,
            "rep_given_today": {"date": str(date.today()), "count": 0, "targets": []},
            "rep_received_today": 0,
            "join_date": str(date.today()),
            "username": None,
            "first_name": None
        }
    u = db["users"][key]
    # Миграция старой структуры rep_given_today
    if not isinstance(u.get("rep_given_today"), dict) or "date" not in u.get("rep_given_today", {}):
        u["rep_given_today"] = {"date": str(date.today()), "count": 0, "targets": []}
    return u

def get_rep_title(rep: int, group: dict = None) -> str:
    """Возвращает титул по репутации. Группа задаёт свои титулы через !добавититул."""
    titles = group.get("rep_titles", []) if group else []
    if not titles:
        return f'{E["star"]} <b>{rep}</b> реп.'
    for t in sorted(titles, key=lambda x: x["min"]):
        if t["min"] <= rep <= t["max"]:
            return t["title"]
    if rep < titles[0]["min"]:
        return titles[0]["title"]
    return titles[-1]["title"]

def get_role_label(db: dict, user_id: int, chat_id: int) -> str:
    group = get_group(db, chat_id)
    uid = str(user_id)
    if user_id == OWNER_ID:
        return f'{E["crown"]} Создатель бота (Глобальный овнер)'
    owner_id = group.get("owner_id")
    if owner_id is not None and user_id == owner_id:
        return f'{E["crown"]} Владелец группы'
    if uid in group["staff"]["senior_admins"]:
        return f'{E["star"]} Старший админ'
    if uid in group["staff"]["admins"]:
        return f'{E["shield"]} Администратор'
    if uid in group["staff"]["mods"]:
        return f'{E["profile"]} Модератор'
    return f'{E["profile"]} Участник'

def is_staff(db: dict, user_id: int, chat_id: int) -> bool:
    group = get_group(db, chat_id)
    uid = str(user_id)
    owner_id = group.get("owner_id")
    return (
        user_id == OWNER_ID
        or (owner_id is not None and user_id == owner_id)
        or uid in group["staff"]["admins"]
        or uid in group["staff"]["senior_admins"]
        or uid in group["staff"]["mods"]
    )

def is_admin(db: dict, user_id: int, chat_id: int) -> bool:
    group = get_group(db, chat_id)
    uid = str(user_id)
    owner_id = group.get("owner_id")
    return (
        user_id == OWNER_ID
        or (owner_id is not None and user_id == owner_id)
        or uid in group["staff"]["admins"]
        or uid in group["staff"]["senior_admins"]
    )

def check_stats_date(group: dict):
    today = date.today()
    today_str = str(today)
    if group.get("stats_date") != today_str:
        group["stats_date"] = today_str
        group["stats_today"] = {}
    week_str = today.strftime("%Y-W%W")
    if group.get("stats_week_label") != week_str:
        group["stats_week_label"] = week_str
        group["stats_week"] = {}
    month_str = today.strftime("%Y-%m")
    if group.get("stats_month_label") != month_str:
        group["stats_month_label"] = month_str
        group["stats_month"] = {}

def mention_html(name: str, user_id: int) -> str:
    return f'<a href="tg://user?id={user_id}">{name}</a>'

def parse_mute_duration(text: str) -> Optional[int]:
    patterns = [
        (r'(\d+)\s*ч', 3600),
        (r'(\d+)\s*час', 3600),
        (r'(\d+)\s*мин', 60),
        (r'(\d+)\s*д', 86400),
        (r'(\d+)\s*сут', 86400),
    ]
    for pattern, mult in patterns:
        m = re.search(pattern, text.lower())
        if m:
            return int(m.group(1)) * mult
    return None

router = Router()

# antispam: {chat_id: {user_id: {"msgs": [(text, ts), ...], "stickers": [ts, ...]}}}
SPAM_TRACKER: dict[int, dict[int, dict]] = {}
SPAM_MSG_LIMIT = 5      # одинаковых сообщений за окно
SPAM_STICKER_LIMIT = 5  # стикеров за окно
SPAM_WINDOW = 30        # секунд

def _check_spam(chat_id: int, uid: int, text: str | None, is_sticker: bool) -> bool:
    now = time.time()
    chat = SPAM_TRACKER.setdefault(chat_id, {})
    user = chat.setdefault(uid, {"msgs": [], "stickers": []})
    # чистим старые
    user["msgs"] = [(t, ts) for t, ts in user["msgs"] if now - ts < SPAM_WINDOW]
    user["stickers"] = [ts for ts in user["stickers"] if now - ts < SPAM_WINDOW]
    if is_sticker:
        user["stickers"].append(now)
        return len(user["stickers"]) >= SPAM_STICKER_LIMIT
    if text:
        user["msgs"].append((text, now))
        same = sum(1 for t, _ in user["msgs"] if t == text)
        return same >= SPAM_MSG_LIMIT
    return False

@router.message(CommandStart())
async def cmd_start(message: Message):
    db = load_db()
    uid = message.from_user.id
    if message.chat.type != "private":
        return
    if uid == OWNER_ID:
        groups = db.get("groups", {})
        total_groups = len(groups)
        total_users = len(db.get("users", {}))
        text = (
            f'{E["crown"]} <b>Панель владельца</b>\n\n'
            f'{E["people"]} Групп подключено: <b>{total_groups}</b>\n'
            f'{E["profile"]} Всего пользователей: <b>{total_users}</b>\n'
            f'{E["shield"]} Глобальных банов: <b>{len(db.get("global_bans", {}))}</b>\n\n'
            f'{E["info"]} Бот активен и работает!'
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Статистика", icon_custom_emoji_id="5278778882848220741", callback_data="owner_stats"),
             InlineKeyboardButton(text="Группы", icon_custom_emoji_id="5298668674532538341", callback_data="owner_groups")],
            [InlineKeyboardButton(text="Глобальные баны", icon_custom_emoji_id="5278578973595427038", callback_data="owner_gbans"),
             InlineKeyboardButton(text="Одобрения", icon_custom_emoji_id="5278411813468269386", callback_data="owner_approvals")],
            [InlineKeyboardButton(text="Рассылка", icon_custom_emoji_id="5278528159837348960", callback_data="owner_broadcast")],
        ])
        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        approved = uid in db.get("approved_owners", [])
        name = message.from_user.first_name or "пользователь"
        warned = db.get("warned_owners", {})
        warn_count = warned.get(str(uid), 0)
        if approved:
            access_line = f'{E["check"]} <b>Одобрен</b>'
        elif warn_count >= 3:
            access_line = f'{E["cross"]} <b>Доступ заблокирован</b>'
        else:
            access_line = f'{E["warn"]} <b>Не одобрен</b>'
        text = (
            f'{E["bot"]} <b>Привет, {name}!</b>\n\n'
            f'{E["profile"]} Пользователь: <b>{name}</b> [<code>{uid}</code>]\n'
            f'{E["shield"]} Уровень доступа: {access_line}\n\n'
            f'{E["info"]} Чтобы добавить бота в группу — нужно одобрение от владельца.'
        )
        buttons = [[InlineKeyboardButton(text="Помощь по командам", icon_custom_emoji_id="5242205011529719330", callback_data="help_main")]]
        if not approved and warn_count < 3:
            buttons.append([InlineKeyboardButton(text="Запросить одобрение", icon_custom_emoji_id="5278411813468269386", callback_data="request_approval_start")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)

@router.callback_query(F.data == "request_approval_start")
async def request_approval_start_cb(call: CallbackQuery):
    """Показываем экран подтверждения заявки."""
    db = load_db()
    uid = call.from_user.id
    if uid in db.get("approved_owners", []):
        await call.answer("Вы уже одобрены!", show_alert=True)
        return
    warned = db.get("warned_owners", {})
    if str(uid) in warned and warned[str(uid)] >= 3:
        await call.answer("Вам заблокирован доступ к боту.", show_alert=True)
        return
    pending = db.get("pending_approval", [])
    already_pending = uid in pending
    if already_pending:
        text = (
            f'{E["clock"]} <b>Заявка уже отправлена</b>\n\n'
            f'Ваша заявка уже находится на рассмотрении у владельца.\n'
            f'Ожидайте ответа от @{OWNER_USERNAME}.'
        )
    else:
        text = (
            f'{E["bell"]} <b>Запрос одобрения</b>\n\n'
            f'{E["profile"]} Ваш аккаунт: <b>{call.from_user.full_name}</b>\n'
            f'{E["info"]} ID: <code>{uid}</code>\n\n'
            f'После отправки заявки владелец бота получит уведомление и рассмотрит ваш запрос.\n'
            f'Вы получите ответ в этом чате.'
        )
    kb_rows = []
    if not already_pending:
        kb_rows.append([InlineKeyboardButton(text="Отправить заявку", icon_custom_emoji_id="5278411813468269386", callback_data="request_approval_confirm")])
    kb_rows.append([InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="back_to_start")])
    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await call.answer()

@router.callback_query(F.data == "request_approval_confirm")
async def request_approval_confirm_cb(call: CallbackQuery):
    """Реально отправляем заявку."""
    db = load_db()
    uid = call.from_user.id
    if uid in db.get("approved_owners", []):
        await call.answer("Вы уже одобрены!", show_alert=True)
        return
    pending = db.get("pending_approval", [])
    if uid not in pending:
        pending.append(uid)
        db["pending_approval"] = pending
        save_db(db)
    name = call.from_user.full_name
    username = call.from_user.username or "нет"
    try:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Одобрить", icon_custom_emoji_id="5278411813468269386", callback_data=f"approve_{uid}"),
             InlineKeyboardButton(text="Отклонить", icon_custom_emoji_id="5278578973595427038", callback_data=f"reject_{uid}")],
        ])
        await call.bot.send_message(
            OWNER_ID,
            f'{E["bell"]} <b>Новая заявка на одобрение</b>\n\n'
            f'{E["profile"]} Имя: <b>{name}</b>\n'
            f'{E["link"]} Username: @{username}\n'
            f'{E["info"]} ID: <code>{uid}</code>',
            parse_mode=ParseMode.HTML,
            reply_markup=kb
        )
    except:
        pass
    await call.message.edit_text(
        f'{E["check"]} <b>Заявка отправлена!</b>\n\n'
        f'Владелец бота @{OWNER_USERNAME} получил ваш запрос.\n'
        f'Вы получите уведомление о решении в этом чате.\n\n'
        f'{E["clock"]} Ожидайте ответа.',
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="back_to_start")]
        ])
    )
    await call.answer()

# Оставляем старый колбэк для совместимости
@router.callback_query(F.data == "request_approval")
async def request_approval_cb(call: CallbackQuery):
    await request_approval_start_cb(call)

@router.callback_query(F.data == "back_to_start")
async def back_to_start_cb(call: CallbackQuery):
    db = load_db()
    uid = call.from_user.id
    approved = uid in db.get("approved_owners", [])
    name = call.from_user.first_name or "пользователь"
    warned = db.get("warned_owners", {})
    warn_count = warned.get(str(uid), 0)
    if approved:
        access_line = f'{E["check"]} <b>Одобрен</b>'
    elif warn_count >= 3:
        access_line = f'{E["cross"]} <b>Доступ заблокирован</b>'
    else:
        access_line = f'{E["warn"]} <b>Не одобрен</b>'
    text = (
        f'{E["bot"]} <b>Привет, {name}!</b>\n\n'
        f'{E["profile"]} Пользователь: <b>{name}</b> [<code>{uid}</code>]\n'
        f'{E["shield"]} Уровень доступа: {access_line}\n\n'
        f'{E["info"]} Чтобы добавить бота в группу — нужно одобрение от владельца.'
    )
    buttons = [[InlineKeyboardButton(text="Помощь по командам", icon_custom_emoji_id="5242205011529719330", callback_data="help_main")]]
    if not approved and warn_count < 3:
        buttons.append([InlineKeyboardButton(text="Запросить одобрение", icon_custom_emoji_id="5278411813468269386", callback_data="request_approval_start")])
    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await call.answer()

@router.callback_query(F.data.startswith("approve_"))
async def approve_owner_cb(call: CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Нет доступа", show_alert=True)
        return
    uid = int(call.data.split("_")[1])
    db = load_db()
    if uid not in db.get("approved_owners", []):
        db["approved_owners"].append(uid)
    if uid in db.get("pending_approval", []):
        db["pending_approval"].remove(uid)
    save_db(db)
    try:
        await call.bot.send_message(
            uid,
            f'{E["check"]} <b>Ваша заявка одобрена!</b>\n\nТеперь вы можете добавить бота в свою группу.',
            parse_mode=ParseMode.HTML
        )
    except:
        pass
    await call.message.edit_text(
        call.message.text + f'\n\n{E["check"]} <b>Одобрено</b>',
        parse_mode=ParseMode.HTML
    )
    await call.answer("Одобрено!")

@router.callback_query(F.data.startswith("reject_"))
async def reject_owner_cb(call: CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Нет доступа", show_alert=True)
        return
    uid = int(call.data.split("_")[1])
    db = load_db()
    if uid in db.get("pending_approval", []):
        db["pending_approval"].remove(uid)
    warned = db.get("warned_owners", {})
    warned[str(uid)] = warned.get(str(uid), 0) + 1
    db["warned_owners"] = warned
    save_db(db)
    count = warned[str(uid)]
    try:
        if count >= 3:
            await call.bot.send_message(uid, f'{E["cross"]} <b>Вам заблокирован доступ к боту.</b>\n\nВы получили 3/3 предупреждений.', parse_mode=ParseMode.HTML)
        else:
            await call.bot.send_message(uid, f'{E["warn"]} <b>Заявка отклонена.</b>\n\nПредупреждение {count}/3. При 3/3 доступ будет заблокирован.', parse_mode=ParseMode.HTML)
    except:
        pass
    await call.message.edit_text(call.message.text + f'\n\n{E["cross"]} <b>Отклонено ({count}/3)</b>', parse_mode=ParseMode.HTML)
    await call.answer("Отклонено!")

@router.my_chat_member()
async def bot_member_updated(update: ChatMemberUpdated):
    old_status = update.old_chat_member.status
    new_status = update.new_chat_member.status
    chat = update.chat
    actor = update.from_user

    # Бот снят с администраторов — выдать варн тому, кто это сделал
    if old_status == ChatMemberStatus.ADMINISTRATOR and new_status == ChatMemberStatus.MEMBER:
        db = load_db()
        if str(chat.id) in db.get("groups", {}):
            if actor.id != OWNER_ID:
                udata_actor = get_user(db, actor.id, chat.id)
                udata_actor["warns"] = udata_actor.get("warns", 0) + 1
                warns = udata_actor["warns"]
                save_db(db)
                try:
                    await update.bot.send_message(
                        chat.id,
                        f'{E["warn"]} {mention_html(actor.full_name, actor.id)} получает предупреждение [<b>{warns}/3</b>] за снятие прав бота.\n'
                        f'<blockquote>Бот под защитой. Попытка его ограничить — нарушение.</blockquote>',
                        parse_mode=ParseMode.HTML
                    )
                except:
                    pass
        return

    # Бот кикнут/забанен — предупреждение и ничего сделать нельзя
    if new_status in [ChatMemberStatus.KICKED, ChatMemberStatus.BANNED, ChatMemberStatus.LEFT]:
        return

    # Бот добавлен или восстановлен
    if new_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR]:
        adder = actor
        db = load_db()
        uid = adder.id
        approved = uid in db.get("approved_owners", []) or uid == OWNER_ID
        if not approved:
            warned = db.get("warned_owners", {})
            warned[str(uid)] = warned.get(str(uid), 0) + 1
            db["warned_owners"] = warned
            save_db(db)
            count = warned[str(uid)]
            try:
                await update.bot.send_message(
                    chat.id,
                    f'{E["warn"]} <b>Внимание!</b>\n\nЭтот пользователь не имеет одобрения для добавления бота.\nБот не будет выполнять команды.\n\nПредупреждение {count}/3',
                    parse_mode=ParseMode.HTML
                )
            except:
                pass
            try:
                await update.bot.send_message(
                    uid,
                    f'{E["warn"]} <b>Предупреждение {count}/3</b>\n\nВы добавили бота без одобрения. При 3/3 доступ будет заблокирован.',
                    parse_mode=ParseMode.HTML
                )
            except:
                pass
            return
        g = get_group(db, chat.id)
        # Сохраняем владельца группы — кто добавил бота
        if g.get("owner_id") is None:
            g["owner_id"] = uid
        save_db(db)
        name = chat.title or "группа"
        try:
            await update.bot.send_message(
                chat.id,
                f'{E["bot"]} <b>Привет! Я seyats — модератор!</b>\n\n'
                f'Добавьте меня в администраторы и я буду следить за порядком в <b>{name}</b>.\n\n'
                f'{E["info"]} Напишите <b>!хелп</b> для списка команд.',
                parse_mode=ParseMode.HTML
            )
        except:
            pass
        try:
            await update.bot.send_message(
                uid,
                f'{E["check"]} <b>Бот успешно добавлен в группу:</b> <b>{name}</b>\n\n'
                f'{E["info"]} ID группы: <code>{chat.id}</code>',
                parse_mode=ParseMode.HTML
            )
        except:
            pass

def check_group_access(db: dict, chat_id: int, user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    key = str(chat_id)
    if key not in db.get("groups", {}):
        return False
    return True

async def _owner_is_blocked(message: Message) -> bool:
    db = load_db()
    warned = db.get("warned_owners", {})
    try:
        admins = await message.bot.get_chat_administrators(message.chat.id)
        for a in admins:
            if a.status == ChatMemberStatus.CREATOR:
                return str(a.user.id) in warned and warned[str(a.user.id)] >= 3
    except:
        pass
    return False

async def check_access_info(message: Message) -> bool:
    """Информационные команды — работают в любой зарегистрированной ИЛИ незарегистрированной группе,
    кроме случая когда добавивший получил 3 предупреждения."""
    if message.chat.type == "private":
        return True
    return not await _owner_is_blocked(message)

async def check_access_and_reply(message: Message) -> bool:
    """Модерационные команды — только в зарегистрированных группах."""
    if message.chat.type == "private":
        return True
    if await _owner_is_blocked(message):
        return False
    db = load_db()
    if str(message.chat.id) not in db.get("groups", {}):
        return False
    return True

@router.message(F.text.regexp(r'(?i)^[!]хелп$'))
async def cmd_help(message: Message):
    if not await check_access_info(message):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Наказания", icon_custom_emoji_id="5278578973595427038", callback_data="help_punish"),
         InlineKeyboardButton(text="Снятие наказаний", icon_custom_emoji_id="5278411813468269386", callback_data="help_unpunish")],
        [InlineKeyboardButton(text="Права персонала", icon_custom_emoji_id="5276262671962892944", callback_data="help_rights"),
         InlineKeyboardButton(text="Репорт", icon_custom_emoji_id="5278589204207528856", callback_data="help_report")],
        [InlineKeyboardButton(text="Информация", icon_custom_emoji_id="5278753302023004775", callback_data="help_info"),
         InlineKeyboardButton(text="Настройки", icon_custom_emoji_id="5278602437001767574", callback_data="help_settings")],
        [InlineKeyboardButton(text="Цензура", icon_custom_emoji_id="5278578973595427038", callback_data="help_censorship"),
         InlineKeyboardButton(text="Репутация", icon_custom_emoji_id="5276111746812112286", callback_data="help_rep")],
        [InlineKeyboardButton(text="Все команды", icon_custom_emoji_id="5278753302023004775", callback_data="help_all")],
    ])
    await message.reply(
        f'{E["bot"]} <b>Меню помощи</b>\nВыберите категорию:',
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

@router.callback_query(F.data == "help_main")
async def help_main_cb(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Наказания", icon_custom_emoji_id="5278578973595427038", callback_data="help_punish"),
         InlineKeyboardButton(text="Снятие наказаний", icon_custom_emoji_id="5278411813468269386", callback_data="help_unpunish")],
        [InlineKeyboardButton(text="Права персонала", icon_custom_emoji_id="5276262671962892944", callback_data="help_rights"),
         InlineKeyboardButton(text="Репорт", icon_custom_emoji_id="5278589204207528856", callback_data="help_report")],
        [InlineKeyboardButton(text="Информация", icon_custom_emoji_id="5278753302023004775", callback_data="help_info"),
         InlineKeyboardButton(text="Настройки", icon_custom_emoji_id="5278602437001767574", callback_data="help_settings")],
        [InlineKeyboardButton(text="Цензура", icon_custom_emoji_id="5278578973595427038", callback_data="help_censorship"),
         InlineKeyboardButton(text="Репутация", icon_custom_emoji_id="5276111746812112286", callback_data="help_rep")],
        [InlineKeyboardButton(text="Все команды", icon_custom_emoji_id="5278753302023004775", callback_data="help_all")],
    ])
    await call.message.edit_text(
        f'{E["bot"]} <b>Меню помощи</b>\nВыберите категорию:',
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

@router.callback_query(F.data == "help_all")
async def help_all_cb(call: CallbackQuery):
    text = (
        f'{E["book"]} <b>Все команды бота</b>\n\n'
        f'<b>Наказания:</b>\n'
        f'<code>!бан</code> — бан навсегда\n'
        f'<code>!мут</code> 1ч/30мин — мут (не может писать)\n'
        f'<code>!тихий</code> 1ч — тихий мут\n'
        f'<code>!кик</code> — кик из чата\n'
        f'<code>!варн</code> [причина] — предупреждение (3/3 = мут 7д)\n'
        f'<code>!гбан</code> — глобальный бан (владелец)\n\n'
        f'<b>Снятие наказаний:</b>\n'
        f'<code>!разбан</code> — снять бан\n'
        f'<code>!размут</code> — снять мут\n'
        f'<code>!анварн</code> — снять 1 варн\n'
        f'<code>!разгбан</code> — снять глобальный бан\n\n'
        f'<b>Персонал:</b>\n'
        f'<code>!модер</code> — назначить модератора\n'
        f'<code>!админ</code> — назначить администратора\n'
        f'<code>!сеньор</code> — назначить ст. админа\n'
        f'<code>!деадмин</code> — снять с должности\n\n'
        f'<b>Цензура:</b>\n'
        f'<code>!цензура добавить слово1,слово2</code>\n'
        f'<code>!цензура удалить слово</code>\n'
        f'<code>!цензура список</code>\n'
        f'<code>!цензура очистить</code>\n\n'
        f'<b>Информация:</b>\n'
        f'<code>!стафф</code> — персонал\n'
        f'<code>!правила</code> — правила чата\n'
        f'<code>!топ</code> / <code>!топ день/неделя/месяц/вся</code>\n'
        f'<code>!рейтинг</code> — репутация\n'
        f'<code>!репутация</code> — топ-25\n'
        f'<code>!инфо</code> — профиль\n'
        f'<code>!история</code> — нарушения\n'
        f'<code>!предупреждения</code> — варны\n'
        f'<code>!кто</code> — роль (ответ)\n'
        f'<code>!обо мне</code> — мой профиль\n'
        f'<code>!чат</code> — инфо о чате\n'
        f'<code>!мои варны</code> — мои предупреждения\n'
        f'<code>!статус</code> — статус функций\n\n'
        f'<b>Настройки:</b>\n'
        f'<code>!панель</code> — панель управления\n'
        f'<code>!настройки</code> — быстрые настройки\n'
        f'<code>!сетправила</code> [текст] — установить правила\n'
        f'<code>!ссылка</code> [название] — инвайт-ссылка\n'
        f'<code>!пин</code> — закрепить (ответ)\n'
        f'<code>!откреп</code> — открепить всё\n'
        f'<code>!объявление</code> [текст] — объявление\n'
        f'<code>!чистка</code> [N] — удалить N сообщений\n'
        f'<code>!грассылка</code> [текст] — рассылка в группе\n'
        f'<code>!рассылка</code> [текст] — глобальная рассылка\n\n'
        f'<b>Репутация:</b>\n'
        f'<code>!репзнак</code> +5/-3 — изменить репутацию\n'
        f'<code>!добавититул</code> [мин] [макс] [название]\n'
        f'<code>!удалититул</code> [номер]\n'
        f'<code>!титулы</code> — список титулов\n\n'
        f'{E["info"]} Все команды применяются ответом на сообщение.'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="help_main")]
    ])
    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

@router.callback_query(F.data == "help_punish")
async def help_punish_cb(call: CallbackQuery):
    text = (
        f'{E["warn"]} <b>Наказания</b>\n\n'
        f'<b>L</b> <code>!бан</code> [причина] — бан навсегда\n'
        f'<b>L</b> <code>!мут</code> 1ч/30мин [причина] — мут (нельзя писать)\n'
        f'<b>L</b> <code>!тихий</code> 1ч/30мин — тихий мут без уведомления\n'
        f'<b>L</b> <code>!кик</code> [причина] — кик из чата\n'
        f'<b>L</b> <code>!варн</code> [причина] — предупреждение (3/3 = мут 7д)\n'
        f'<b>L</b> <code>!гбан</code> — глобальный бан (только владелец)\n'
        f'<b>L</b> <code>!объявление</code> [текст] — объявление от бота\n'
        f'<b>L</b> <code>!чистка</code> [N=10] — удалить N последних сообщений\n\n'
        f'{E["info"]} Команды применяются <b>ответом</b> на сообщение.'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="help_main")]
    ])
    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

@router.callback_query(F.data == "help_censorship")
async def help_censorship_cb(call: CallbackQuery):
    text = (
        f'{E["shield"]} <b>Цензура</b>\n\n'
        f'<b>L</b> <code>!цензура добавить [слово]</code> — добавить слово в чёрный список\n'
        f'<b>L</b> <code>!цензура удалить [слово]</code> — убрать слово из списка\n'
        f'<b>L</b> <code>!цензура список</code> — показать все запрещённые слова\n'
        f'<b>L</b> <code>!цензура очистить</code> — удалить все слова\n\n'
        f'{E["info"]} Бот молча удаляет сообщения с запрещёнными словами.\n'
        f'Настроить в панели: <code>!панель</code> → Цензура'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="help_main")]
    ])
    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

@router.callback_query(F.data == "help_rep")
async def help_rep_cb(call: CallbackQuery):
    text = (
        f'{E["star"]} <b>Репутация</b>\n\n'
        f'<b>Как работает:</b>\n'
        f'Ответь на сообщение одним из триггеров.\n\n'
        f'<b>Повышение:</b> <code>+</code>, <code>++</code>, <code>+реп</code>, <code>уважение</code>, <code>красава</code>, <code>огонь</code>, <code>топ</code>, <code>молодец</code>, <code>спасибо</code>, <code>gg</code> и др.\n\n'
        f'<b>Понижение:</b> <code>-</code>, <code>--</code>, <code>-реп</code>, <code>диз</code>, <code>бред</code>, <code>кринж</code>, <code>зашквар</code>, <code>дно</code> и др.\n\n'
        f'<b>L</b> <code>!рейтинг</code> [@user] — репутация пользователя\n'
        f'<b>L</b> <code>!репутация</code> — топ-25 по репутации\n'
        f'<b>L</b> <code>!репзнак</code> +5/-3 — изменить вручную (персонал)\n'
        f'<b>L</b> <code>!титулы</code> — список титулов по репутации\n'
        f'<b>L</b> <code>!добавититул</code> [мин] [макс] [название]\n'
        f'<b>L</b> <code>!удалититул</code> [номер]\n\n'
        f'{E["info"]} Лимит: 5 оценок в день (меняется в панели).'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="help_main")]
    ])
    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

@router.callback_query(F.data == "help_unpunish")
async def help_unpunish_cb(call: CallbackQuery):
    text = (
        f'{E["check"]} <b>Снятие наказаний</b>\n\n'
        f'<b>L</b> <code>!разбан</code> — снять бан\n'
        f'<b>L</b> <code>!размут</code> — снять мут\n'
        f'<b>L</b> <code>!анварн</code> — снять 1 предупреждение\n'
        f'<b>L</b> <code>!разгбан</code> — снять глобальный бан (владелец)\n\n'
        f'{E["info"]} Ответьте на сообщение пользователя.'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="help_main")]
    ])
    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

@router.callback_query(F.data == "help_report")
async def help_report_cb(call: CallbackQuery):
    text = (
        f'{E["bell"]} <b>Жалобы (Репорты)</b>\n\n'
        f'<b>L</b> <code>!репорт</code> — ответом на нарушение\n'
        f'Бот тегнет администраторов и пришлёт кнопки быстрого реагирования.'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="help_main")]
    ])
    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

@router.callback_query(F.data == "help_info")
async def help_info_cb(call: CallbackQuery):
    text = (
        f'{E["info"]} <b>Запросы информации</b>\n\n'
        f'<b>L</b> <code>!стафф</code> — список персонала группы\n'
        f'<b>L</b> <code>!правила</code> — правила сообщества\n'
        f'<b>L</b> <code>!топ</code> / <code>!топ день</code> / <code>!топ неделя</code> / <code>!топ месяц</code> / <code>!топ вся</code>\n'
        f'<b>L</b> <code>!рейтинг</code> [@user/id/reply] — репутация\n'
        f'<b>L</b> <code>!репутация</code> — топ-25 по репутации\n'
        f'<b>L</b> <code>!инфо</code> — профиль пользователя\n'
        f'<b>L</b> <code>!история</code> — история нарушений\n'
        f'<b>L</b> <code>!предупреждения</code> — варны пользователя\n'
        f'<b>L</b> <code>!кто</code> — роль и репутация (ответ)\n'
        f'<b>L</b> <code>!обо мне</code> — ваш профиль\n'
        f'<b>L</b> <code>!чат</code> — информация о чате\n'
        f'<b>L</b> <code>!мои варны</code> — ваши предупреждения\n'
        f'<b>L</b> <code>!статус</code> — статус функций группы\n'
        f'<b>L</b> <code>!титулы</code> — титулы репутации\n'
        f'<b>L</b> <code>!цензура список</code> — запрещённые слова'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="help_main")]
    ])
    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

@router.callback_query(F.data == "help_settings")
async def help_settings_cb(call: CallbackQuery):
    text = (
        f'{E["settings"]} <b>Настройки</b>\n\n'
        f'<b>L</b> <code>!панель</code> — полная панель управления группой\n'
        f'<b>L</b> <code>!настройки</code> — быстрые настройки\n'
        f'<b>L</b> <code>!сетправила</code> [текст] — обновить правила\n'
        f'<b>L</b> <code>!ссылка</code> [название] — создать инвайт-ссылку\n'
        f'<b>L</b> <code>!пин</code> — закрепить сообщение (ответ)\n'
        f'<b>L</b> <code>!откреп</code> — открепить все сообщения\n'
        f'<b>L</b> <code>!рассылка</code> [текст] — рассылка во все группы (владелец бота)\n'
        f'<b>L</b> <code>!грассылка</code> [текст] — рассылка в текущую группу (админ)\n\n'
        f'{E["info"]} Включить/выключить в <code>!панель</code>:\n'
        f'приветствие, антифлуд, антиссылки, антиспам, цензура'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="help_main")]
    ])
    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

@router.callback_query(F.data == "help_rights")
async def help_rights_cb(call: CallbackQuery):
    text = (
        f'{E["shield"]} <b>Права персонала</b>\n\n'
        f'<b>L</b> <code>!модер</code> — назначить модератора (ответ)\n'
        f'<b>L</b> <code>!админ</code> — назначить администратора (ответ)\n'
        f'<b>L</b> <code>!сеньор</code> — назначить ст. админа (ответ)\n'
        f'<b>L</b> <code>!деадмин</code> — снять с должности (ответ)\n\n'
        f'Или через <code>!панель</code> → Персонал — визуальный менеджер.\n\n'
        f'{E["info"]} Назначать администраторов — только владелец.\n'
        f'Назначать модераторов — любой администратор.'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="help_main")]
    ])
    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

@router.message(F.text.regexp(r'(?i)^[!]правила$'))
async def cmd_rules(message: Message):
    if not await check_access_info(message):
        return
    db = load_db()
    group = get_group(db, message.chat.id)
    rules = group.get("rules", "Правила не установлены.")
    await message.reply(
        f'{E["book"]} <b>Правила чата</b>\n\n'
        f'<blockquote>{rules}\n\nНаказания:\n• 1 нарушение — предупреждение.\n• 2 нарушение — мут.\n• 3 нарушение — бан.\n\n<i>Повторный бан после разбана — без предупреждений.</i></blockquote>\n\n'
        f'{E["link"]} Канал: {CHANNEL}',
        parse_mode=ParseMode.HTML
    )

@router.message(F.text.regexp(r'(?i)^[!]стафф$'))
async def cmd_staff(message: Message):
    if not await check_access_info(message):
        return
    db = load_db()
    group = get_group(db, message.chat.id)
    staff = group.get("staff", {})

    senior_lines = []
    for uid_str in staff.get("senior_admins", []):
        try:
            member = await message.bot.get_chat_member(message.chat.id, int(uid_str))
            name = member.user.full_name
            uname = f"@{member.user.username}" if member.user.username else f"[{uid_str}]"
            senior_lines.append(f'<b>L</b> {mention_html(name, int(uid_str))} {uname} [<code>{uid_str}</code>] {E["star"]}')
        except:
            pass

    admin_lines = []
    for uid_str in staff.get("admins", []):
        try:
            member = await message.bot.get_chat_member(message.chat.id, int(uid_str))
            name = member.user.full_name
            uname = f"@{member.user.username}" if member.user.username else f"[{uid_str}]"
            admin_lines.append(f'<b>L</b> {mention_html(name, int(uid_str))} {uname} [<code>{uid_str}</code>] {E["shield"]}')
        except:
            pass

    mod_lines = []
    for uid_str in staff.get("mods", []):
        try:
            member = await message.bot.get_chat_member(message.chat.id, int(uid_str))
            name = member.user.full_name
            uname = f"@{member.user.username}" if member.user.username else f"[{uid_str}]"
            mod_lines.append(f'<b>L</b> {mention_html(name, int(uid_str))} {uname} [<code>{uid_str}</code>] {E["profile"]}')
        except:
            pass

    text = f'{E["pc"]} <b>Администрация чата</b>\n\n'
    text += f'{E["star"]} <b>Старшие админы:</b>\n'
    text += ('\n'.join(senior_lines) if senior_lines else f'<i>Нет старших админов</i>') + '\n\n'
    text += f'{E["shield"]} <b>Администраторы:</b>\n'
    text += ('\n'.join(admin_lines) if admin_lines else f'<i>Нет администраторов</i>') + '\n\n'
    text += f'{E["profile"]} <b>Модераторы:</b>\n'
    text += ('\n'.join(mod_lines) if mod_lines else f'<i>Нет модераторов</i>')

    await message.reply(text, parse_mode=ParseMode.HTML)

@router.message(F.text.regexp(r'(?i)^[!](репа|репутация|реп)$'))
async def cmd_reputation_top(message: Message):
    if not await check_access_info(message):
        return
    db = load_db()
    chat_id = message.chat.id
    users_in_chat = {k: v for k, v in db["users"].items() if v.get("chat_id") == chat_id}
    sorted_users = sorted(users_in_chat.values(), key=lambda x: x.get("reputation", 0), reverse=True)[:25]
    group = get_group(db, chat_id)
    lines = []
    for i, u in enumerate(sorted_users, 1):
        rep = u.get("reputation", 0)
        name = u.get("first_name") or u.get("username") or f'[{u["user_id"]}]'
        title = get_rep_title(rep, group)
        lines.append(f'<b>{i}.</b> {mention_html(name, u["user_id"])} — <b>{rep} реп.</b> ({title})')
    text = f'{E["star"]} <b>Топ репутации участников:</b>\n\n' + '\n'.join(lines) if lines else f'{E["info"]} Пока никто не имеет репутации.'
    await message.reply(text, parse_mode=ParseMode.HTML)

@router.message(F.text.regexp(r'(?i)^[!]рейтинг'))
async def cmd_rating(message: Message):
    if not await check_access_info(message):
        return
    db = load_db()
    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    else:
        parts = message.text.split()
        if len(parts) > 1:
            arg = parts[1]
            if arg.startswith("@"):
                uname = arg[1:].lower()
                for u in db["users"].values():
                    if u.get("username", "").lower() == uname and u.get("chat_id") == message.chat.id:
                        class FakeUser:
                            id = u["user_id"]
                            full_name = u.get("first_name") or uname
                            username = u.get("username")
                        target = FakeUser()
                        break
            elif arg.isdigit():
                uid2 = int(arg)
                key2 = f"{message.chat.id}_{uid2}"
                if key2 in db["users"]:
                    u = db["users"][key2]
                    class FakeUser2:
                        id = uid2
                        full_name = u.get("first_name") or str(uid2)
                        username = u.get("username")
                    target = FakeUser2()
        else:
            target = message.from_user
    if not target:
        target = message.from_user
    udata = get_user(db, target.id, message.chat.id)
    rep = udata.get("reputation", 0)
    group = get_group(db, message.chat.id)
    title = get_rep_title(rep, group)
    name = target.full_name or str(target.id)
    await message.reply(
        f'{E["bot"]} <b>Репутация {mention_html(name, target.id)}:</b> <b>{rep}</b>\n'
        f'<b>L</b> Статус: {title}',
        parse_mode=ParseMode.HTML
    )

def _top_lines_from_group_stats(stats: dict, limit: int = 15) -> list[str]:
    sorted_s = sorted(stats.items(), key=lambda x: x[1].get("count", 0), reverse=True)[:limit]
    lines = []
    for i, (uid_str, stat) in enumerate(sorted_s, 1):
        count = stat.get("count", 0)
        name = stat.get("name", uid_str)
        lines.append(f'<b>{i}.</b> {mention_html(name, int(uid_str))} — <b>{count} сообщ.</b>')
    return lines

def _top_lines_from_users(db: dict, chat_id: int, field: str, limit: int = 15) -> list[str]:
    users_in_chat = [v for v in db["users"].values() if v.get("chat_id") == chat_id]
    sorted_u = sorted(users_in_chat, key=lambda x: x.get(field, 0), reverse=True)[:limit]
    lines = []
    for i, u in enumerate(sorted_u, 1):
        count = u.get(field, 0)
        name = u.get("first_name") or u.get("username") or f'[{u["user_id"]}]'
        lines.append(f'<b>{i}.</b> {mention_html(name, u["user_id"])} — <b>{count} сообщ.</b>')
    return lines

@router.message(F.text.regexp(r'(?i)^[!]топ день$'))
async def cmd_top_day(message: Message):
    if not await check_access_info(message):
        return
    db = load_db()
    group = get_group(db, message.chat.id)
    check_stats_date(group)
    lines = _top_lines_from_group_stats(group.get("stats_today", {}))
    save_db(db)
    text = f'{E["chart"]} <b>Топ за сегодня:</b>\n\n' + '\n'.join(lines) if lines else f'{E["info"]} Нет данных за сегодня.'
    await message.reply(text, parse_mode=ParseMode.HTML)

@router.message(F.text.regexp(r'(?i)^[!]топ неделя$'))
async def cmd_top_week(message: Message):
    if not await check_access_info(message):
        return
    db = load_db()
    group = get_group(db, message.chat.id)
    check_stats_date(group)
    lines = _top_lines_from_group_stats(group.get("stats_week", {}))
    save_db(db)
    text = f'{E["chart"]} <b>Топ за эту неделю:</b>\n\n' + '\n'.join(lines) if lines else f'{E["info"]} Нет данных за эту неделю.'
    await message.reply(text, parse_mode=ParseMode.HTML)

@router.message(F.text.regexp(r'(?i)^[!]топ месяц$'))
async def cmd_top_month(message: Message):
    if not await check_access_info(message):
        return
    db = load_db()
    group = get_group(db, message.chat.id)
    check_stats_date(group)
    lines = _top_lines_from_group_stats(group.get("stats_month", {}))
    save_db(db)
    text = f'{E["chart"]} <b>Топ за этот месяц:</b>\n\n' + '\n'.join(lines) if lines else f'{E["info"]} Нет данных за этот месяц.'
    await message.reply(text, parse_mode=ParseMode.HTML)

@router.message(F.text.regexp(r'(?i)^[!](топ вся|топ всё|топ все)$'))
async def cmd_top_all(message: Message):
    if not await check_access_info(message):
        return
    db = load_db()
    lines = _top_lines_from_users(db, message.chat.id, "stats_all_count")
    text = f'{E["chart"]} <b>Топ за всё время:</b>\n\n' + '\n'.join(lines) if lines else f'{E["info"]} Нет данных.'
    await message.reply(text, parse_mode=ParseMode.HTML)

@router.message(F.text.regexp(r'(?i)^[!]топ$'))
async def cmd_top_today(message: Message):
    if not await check_access_info(message):
        return
    db = load_db()
    group = get_group(db, message.chat.id)
    check_stats_date(group)
    lines = _top_lines_from_group_stats(group.get("stats_today", {}))
    save_db(db)
    text = (
        f'{E["chart"]} <b>Топ активности</b>\n\n'
        f'<b>L</b> <code>!топ день</code> — сегодня\n'
        f'<b>L</b> <code>!топ неделя</code> — эта неделя\n'
        f'<b>L</b> <code>!топ месяц</code> — этот месяц\n'
        f'<b>L</b> <code>!топ вся</code> — за всё время\n\n'
        f'{E["chart"]} <b>Сегодня:</b>\n\n' + ('\n'.join(lines) if lines else 'Нет данных за сегодня.')
    )
    await message.reply(text, parse_mode=ParseMode.HTML)

@router.message(F.text.regexp(r'(?i)^[!]инфо$'))
async def cmd_info(message: Message):
    if not await check_access_info(message):
        return
    db = load_db()
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    else:
        target = message.from_user
    chat_id = message.chat.id
    udata = get_user(db, target.id, chat_id)
    rep = udata.get("reputation", 0)
    warns = udata.get("warns", 0)
    violations = udata.get("violations", 0)
    muted_until = udata.get("muted_until")
    banned = udata.get("banned", False)
    role = get_role_label(db, target.id, chat_id)
    username_line = f'@{target.username}' if target.username else 'нет'
    mute_status = f'{E["cross"]} Ограничений нет' if not muted_until else f'{E["warn"]} До {muted_until}'
    ban_status = f'{E["cross"]} Ограничений нет' if not banned else f'{E["warn"]} Забанен'
    text = (
        f'{E["bot"]} <b>Информация о пользователе {target.full_name}</b>\n\n'
        f'<blockquote><b>Основная информация</b>\n'
        f'<b>L</b> ID: <code>{target.id}</code>\n'
        f'<b>L</b> Юзернейм: {username_line}</blockquote>\n\n'
        f'<blockquote><b>Статус и права в группе</b>\n'
        f'<b>L</b> Статус: {role}\n'
        f'<b>L</b> Доступ: {role}</blockquote>\n\n'
        f'<blockquote><b>Статистика и история</b>\n'
        f'<b>L</b> Репутация: <b>{rep}</b>\n'
        f'<b>L</b> Варны: <b>{warns}</b> из 3\n'
        f'<b>L</b> Всего нарушений в базе: <b>{violations}</b></blockquote>\n\n'
        f'<blockquote><b>Активные наказания</b>\n'
        f'<b>L</b> Мут: {mute_status}\n'
        f'<b>L</b> Бан: {ban_status}</blockquote>'
    )
    await message.reply(text, parse_mode=ParseMode.HTML)

@router.message(F.text.regexp(r'(?i)^[!]варн'))
async def cmd_warn(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_staff(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только персонал может выдавать предупреждения.</b>', parse_mode=ParseMode.HTML)
        return
    if not message.reply_to_message:
        await message.reply(f'{E["warn"]} <b>Ответьте на сообщение пользователя.</b>', parse_mode=ParseMode.HTML)
        return
    target = message.reply_to_message.from_user
    if target.id == message.from_user.id:
        await message.reply(f'{E["cross"]} <b>Нельзя предупреждать самого себя.</b>', parse_mode=ParseMode.HTML)
        return
    if target.id == OWNER_ID:
        await message.reply(f'{E["cross"]} <b>Нельзя предупреждать владельца.</b>', parse_mode=ParseMode.HTML)
        return
    parts = message.text.split(maxsplit=1)
    reason = parts[1] if len(parts) > 1 else 'не указана'
    udata = get_user(db, target.id, message.chat.id)
    udata["warns"] = udata.get("warns", 0) + 1
    udata["violations"] = udata.get("violations", 0) + 1
    warns = udata["warns"]
    save_db(db)
    mod_name = message.from_user.full_name
    target_name = target.full_name
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="-1", icon_custom_emoji_id="5244796895443838315", callback_data=f"warn_minus_{target.id}"),
         InlineKeyboardButton(text="+1", icon_custom_emoji_id="5242329690135356589", callback_data=f"warn_plus_{target.id}")],
        [InlineKeyboardButton(text="Сброс предупреждений", icon_custom_emoji_id="5278611606756942667", callback_data=f"warn_reset_{target.id}")],
        [InlineKeyboardButton(text="Закрыть", icon_custom_emoji_id="5278578973595427038", callback_data="close_msg")],
    ])
    await message.reply(
        f'{E["profile"]} {mention_html(target_name, target.id)} [<code>{target.id}</code>] получает предупреждение [<b>{warns}/3</b>].\n'
        f'<blockquote>Причина: {reason}\nМодератор: {mention_html(mod_name, message.from_user.id)}</blockquote>',
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )
    await log_action(message.bot, f"ВАРН {warns}/3", message.chat.id, message.chat.title or "",
                     message.from_user.id, mod_name, target.id, target_name, f"причина: {reason}")
    if warns >= 3:
        try:
            until = datetime.now() + timedelta(days=7)
            await message.bot.restrict_chat_member(
                message.chat.id, target.id,
                permissions=ChatPermissions(
                    can_send_messages=False,
                    can_send_audios=False,
                    can_send_documents=False,
                    can_send_photos=False,
                    can_send_videos=False,
                    can_send_video_notes=False,
                    can_send_voice_notes=False,
                    can_send_polls=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False,
                ),
                until_date=until
            )
            udata["muted_until"] = until.strftime("%Y-%m-%d %H:%M")
            udata["warns"] = 3
            save_db(db)
            await message.answer(
                f'{E["lock"]} {mention_html(target_name, target.id)} [<code>{target.id}</code>] получил <b>3/3 предупреждения</b>.\n'
                f'<blockquote>{E["clock"]} Мут на 7 дней\n'
                f'{E["info"]} До: {until.strftime("%d.%m.%Y %H:%M")}</blockquote>',
                parse_mode=ParseMode.HTML
            )
        except:
            pass

@router.callback_query(F.data.startswith("warn_minus_"))
async def warn_minus_cb(call: CallbackQuery):
    db = load_db()
    if not is_staff(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    uid = int(call.data.split("_")[2])
    udata = get_user(db, uid, call.message.chat.id)
    if udata["warns"] > 0:
        udata["warns"] -= 1
    save_db(db)
    await call.answer(f'Предупреждения: {udata["warns"]}/3', show_alert=True)

@router.callback_query(F.data.startswith("warn_plus_"))
async def warn_plus_cb(call: CallbackQuery):
    db = load_db()
    if not is_staff(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    uid = int(call.data.split("_")[2])
    udata = get_user(db, uid, call.message.chat.id)
    udata["warns"] = min(udata.get("warns", 0) + 1, 3)
    save_db(db)
    await call.answer(f'Предупреждения: {udata["warns"]}/3', show_alert=True)

@router.callback_query(F.data.startswith("warn_reset_"))
async def warn_reset_cb(call: CallbackQuery):
    db = load_db()
    if not is_staff(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    uid = int(call.data.split("_")[2])
    udata = get_user(db, uid, call.message.chat.id)
    udata["warns"] = 0
    save_db(db)
    await call.answer("Предупреждения сброшены!", show_alert=True)

@router.callback_query(F.data == "close_msg")
async def close_msg_cb(call: CallbackQuery):
    try:
        await call.message.delete()
    except:
        pass
    await call.answer()

@router.message(F.text.regexp(r'(?i)^[!]анварн$'))
async def cmd_unwarn(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_staff(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только персонал может снимать предупреждения.</b>', parse_mode=ParseMode.HTML)
        return
    if not message.reply_to_message:
        await message.reply(f'{E["warn"]} <b>Ответьте на сообщение пользователя.</b>', parse_mode=ParseMode.HTML)
        return
    target = message.reply_to_message.from_user
    udata = get_user(db, target.id, message.chat.id)
    if udata.get("warns", 0) > 0:
        udata["warns"] -= 1
    save_db(db)
    mod_name = message.from_user.full_name
    await message.reply(
        f'{E["party"]} С {mention_html(target.full_name, target.id)} [<code>{target.id}</code>] снято предупреждение (Осталось: <b>{udata["warns"]}</b>).\n'
        f'<blockquote>Модератор: {mention_html(mod_name, message.from_user.id)}</blockquote>',
        parse_mode=ParseMode.HTML
    )

@router.message(F.text.regexp(r'(?i)^[!]бан'))
async def cmd_ban(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_staff(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только персонал может банить.</b>', parse_mode=ParseMode.HTML)
        return
    if not message.reply_to_message:
        await message.reply(f'{E["warn"]} <b>Ответьте на сообщение пользователя.</b>', parse_mode=ParseMode.HTML)
        return
    target = message.reply_to_message.from_user
    if target.id == OWNER_ID:
        await message.reply(f'{E["cross"]} <b>Нельзя банить владельца.</b>', parse_mode=ParseMode.HTML)
        return
    parts = message.text.split(maxsplit=1)
    reason = parts[1] if len(parts) > 1 else 'не указана'
    udata = get_user(db, target.id, message.chat.id)
    udata["banned"] = True
    udata["violations"] = udata.get("violations", 0) + 1
    save_db(db)
    mod_name = message.from_user.full_name
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Разбанить", icon_custom_emoji_id="5278411813468269386", callback_data=f"unban_{target.id}")]
    ])
    try:
        await message.bot.ban_chat_member(message.chat.id, target.id)
    except TelegramBadRequest as e:
        await message.reply(f'{E["cross"]} Ошибка: {e}', parse_mode=ParseMode.HTML)
        return
    await message.reply(
        f'{E["lock"]} <b>Бессрочный бан выдан.</b>\n\n'
        f'{E["profile"]} {mention_html(target.full_name, target.id)} [<code>{target.id}</code>] заблокирован(а).\n'
        f'<blockquote>Срок: навсегда\nПричина: {reason}\nМодератор: {mention_html(mod_name, message.from_user.id)}</blockquote>',
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )
    await log_action(message.bot, "БАН", message.chat.id, message.chat.title or "",
                     message.from_user.id, mod_name, target.id, target.full_name, f"причина: {reason}")
async def unban_cb(call: CallbackQuery):
    db = load_db()
    if not is_staff(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    uid = int(call.data.split("_")[1])
    try:
        await call.bot.unban_chat_member(call.message.chat.id, uid)
    except:
        pass
    udata = get_user(db, uid, call.message.chat.id)
    udata["banned"] = False
    save_db(db)
    await call.message.edit_reply_markup(reply_markup=None)
    await call.answer("Пользователь разбанен!", show_alert=True)

@router.message(F.text.regexp(r'(?i)^[!]разбан$'))
async def cmd_unban(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_staff(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только персонал может разбанивать.</b>', parse_mode=ParseMode.HTML)
        return
    if not message.reply_to_message:
        await message.reply(f'{E["warn"]} <b>Ответьте на сообщение пользователя.</b>', parse_mode=ParseMode.HTML)
        return
    target = message.reply_to_message.from_user
    try:
        await message.bot.unban_chat_member(message.chat.id, target.id)
    except:
        pass
    udata = get_user(db, target.id, message.chat.id)
    udata["banned"] = False
    save_db(db)
    await message.reply(
        f'{E["unlock"]} {mention_html(target.full_name, target.id)} разбанен(а).',
        parse_mode=ParseMode.HTML
    )

@router.message(F.text.regexp(r'(?i)^[!]мут'))
async def cmd_mute(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_staff(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только персонал может мутить.</b>', parse_mode=ParseMode.HTML)
        return
    if not message.reply_to_message:
        await message.reply(f'{E["warn"]} <b>Ответьте на сообщение пользователя.</b>', parse_mode=ParseMode.HTML)
        return
    target = message.reply_to_message.from_user
    if target.id == OWNER_ID:
        await message.reply(f'{E["cross"]} <b>Нельзя мутить владельца.</b>', parse_mode=ParseMode.HTML)
        return
    parts = message.text.split(maxsplit=1)
    args = parts[1] if len(parts) > 1 else ''
    duration_sec = parse_mute_duration(args)
    reason_text = re.sub(r'\d+\s*(ч|час|мин|д|сут)\w*', '', args).strip() or 'не указана'
    if not duration_sec:
        duration_sec = 3600
        duration_label = "1 час"
    else:
        if duration_sec < 3600:
            duration_label = f'{duration_sec // 60} мин'
        elif duration_sec < 86400:
            duration_label = f'{duration_sec // 3600} ч'
        else:
            duration_label = f'{duration_sec // 86400} д'
    until = datetime.now() + timedelta(seconds=duration_sec)
    udata = get_user(db, target.id, message.chat.id)
    udata["muted_until"] = until.strftime("%Y-%m-%d %H:%M")
    udata["violations"] = udata.get("violations", 0) + 1
    save_db(db)
    mod_name = message.from_user.full_name
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Размутить", icon_custom_emoji_id="5278411813468269386", callback_data=f"unmute_{target.id}")]
    ])
    try:
        await message.bot.restrict_chat_member(
            message.chat.id, target.id,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_send_audios=False,
                can_send_documents=False,
                can_send_photos=False,
                can_send_videos=False,
                can_send_video_notes=False,
                can_send_voice_notes=False,
                can_send_polls=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False,
            ),
            until_date=until
        )
    except TelegramBadRequest as e:
        await message.reply(f'{E["cross"]} Ошибка: {e}', parse_mode=ParseMode.HTML)
        return
    await message.reply(
        f'{E["clock"]} {mention_html(target.full_name, target.id)} [<code>{target.id}</code>] замучен(а).\n'
        f'<blockquote>Срок: <b>{duration_label}</b>\nПричина: {reason_text}\nМодератор: {mention_html(mod_name, message.from_user.id)}</blockquote>',
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )
    await log_action(message.bot, "МУТ", message.chat.id, message.chat.title or "",
                     message.from_user.id, mod_name, target.id, target.full_name,
                     f"срок: {duration_label}, причина: {reason_text}")
async def unmute_cb(call: CallbackQuery):
    db = load_db()
    if not is_staff(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    uid = int(call.data.split("_")[1])
    try:
        await call.bot.restrict_chat_member(
            call.message.chat.id, uid,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            )
        )
    except:
        pass
    udata = get_user(db, uid, call.message.chat.id)
    udata["muted_until"] = None
    save_db(db)
    await call.message.edit_reply_markup(reply_markup=None)
    await call.answer("Пользователь размучен!", show_alert=True)

@router.message(F.text.regexp(r'(?i)^[!]размут$'))
async def cmd_unmute(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_staff(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только персонал может снимать мут.</b>', parse_mode=ParseMode.HTML)
        return
    if not message.reply_to_message:
        await message.reply(f'{E["warn"]} <b>Ответьте на сообщение пользователя.</b>', parse_mode=ParseMode.HTML)
        return
    target = message.reply_to_message.from_user
    try:
        await message.bot.restrict_chat_member(
            message.chat.id, target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            )
        )
    except:
        pass
    udata = get_user(db, target.id, message.chat.id)
    udata["muted_until"] = None
    save_db(db)
    await message.reply(
        f'{E["unlock"]} {mention_html(target.full_name, target.id)} размучен(а).',
        parse_mode=ParseMode.HTML
    )

@router.message(F.text.regexp(r'(?i)^[!]кик'))
async def cmd_kick(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_staff(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только персонал может кикать.</b>', parse_mode=ParseMode.HTML)
        return
    if not message.reply_to_message:
        await message.reply(f'{E["warn"]} <b>Ответьте на сообщение пользователя.</b>', parse_mode=ParseMode.HTML)
        return
    target = message.reply_to_message.from_user
    if target.id == OWNER_ID:
        await message.reply(f'{E["cross"]} <b>Нельзя кикать владельца.</b>', parse_mode=ParseMode.HTML)
        return
    parts = message.text.split(maxsplit=1)
    reason = parts[1] if len(parts) > 1 else 'не указана'
    mod_name = message.from_user.full_name
    try:
        await message.bot.ban_chat_member(message.chat.id, target.id)
        await message.bot.unban_chat_member(message.chat.id, target.id)
    except TelegramBadRequest as e:
        await message.reply(f'{E["cross"]} Ошибка: {e}', parse_mode=ParseMode.HTML)
        return
    udata = get_user(db, target.id, message.chat.id)
    udata["violations"] = udata.get("violations", 0) + 1
    save_db(db)
    await message.reply(
        f'{E["cross"]} {mention_html(target.full_name, target.id)} [<code>{target.id}</code>] кикнут(а).\n'
        f'<blockquote>Причина: {reason}\nМодератор: {mention_html(mod_name, message.from_user.id)}</blockquote>',
        parse_mode=ParseMode.HTML
    )
    await log_action(message.bot, "КИК", message.chat.id, message.chat.title or "",
                     message.from_user.id, mod_name, target.id, target.full_name, f"причина: {reason}")
async def cmd_report(message: Message):
    if not await check_access_and_reply(message):
        return
    if not message.reply_to_message:
        await message.reply(f'{E["warn"]} <b>Ответьте на сообщение нарушителя.</b>', parse_mode=ParseMode.HTML)
        return
    target = message.reply_to_message.from_user
    reporter = message.from_user
    db = load_db()
    group = get_group(db, message.chat.id)
    staff_ids = (
        group["staff"].get("senior_admins", []) +
        group["staff"].get("admins", []) +
        group["staff"].get("mods", [])
    )
    staff_mentions = []
    for sid in staff_ids:
        try:
            member = await message.bot.get_chat_member(message.chat.id, int(sid))
            staff_mentions.append(mention_html(member.user.full_name, int(sid)))
        except:
            pass
    staff_line = " ".join(staff_mentions) if staff_mentions else "нет персонала"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Забанить", icon_custom_emoji_id="5278578973595427038", callback_data=f"rep_ban_{target.id}"),
         InlineKeyboardButton(text="Замутить", icon_custom_emoji_id="5276412364458059956", callback_data=f"rep_mute_{target.id}")],
        [InlineKeyboardButton(text="Предупреждение", icon_custom_emoji_id="5276240711795107620", callback_data=f"rep_warn_{target.id}"),
         InlineKeyboardButton(text="Игнорировать", icon_custom_emoji_id="5278578973595427038", callback_data="close_msg")],
    ])
    await message.reply(
        f'{E["bell"]} <b>Жалоба на {mention_html(target.full_name, target.id)}</b>\n\n'
        f'{E["profile"]} От: {mention_html(reporter.full_name, reporter.id)}\n'
        f'{E["info"]} Сообщение выше является нарушением.\n\n'
        f'{E["mega"]} Персонал: {staff_line}',
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

@router.callback_query(F.data.startswith("rep_ban_"))
async def rep_ban_cb(call: CallbackQuery):
    db = load_db()
    if not is_staff(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    uid = int(call.data.split("_")[2])
    try:
        await call.bot.ban_chat_member(call.message.chat.id, uid)
    except:
        pass
    udata = get_user(db, uid, call.message.chat.id)
    udata["banned"] = True
    save_db(db)
    await call.answer("Забанен!", show_alert=True)
    await call.message.edit_reply_markup(reply_markup=None)

@router.callback_query(F.data.startswith("rep_mute_"))
async def rep_mute_cb(call: CallbackQuery):
    db = load_db()
    if not is_staff(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    uid = int(call.data.split("_")[2])
    until = datetime.now() + timedelta(hours=1)
    try:
        await call.bot.restrict_chat_member(
            call.message.chat.id, uid,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until
        )
    except:
        pass
    udata = get_user(db, uid, call.message.chat.id)
    udata["muted_until"] = until.strftime("%Y-%m-%d %H:%M")
    save_db(db)
    await call.answer("Замучен на 1 час!", show_alert=True)
    await call.message.edit_reply_markup(reply_markup=None)

@router.callback_query(F.data.startswith("rep_warn_"))
async def rep_warn_cb(call: CallbackQuery):
    db = load_db()
    if not is_staff(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    uid = int(call.data.split("_")[2])
    udata = get_user(db, uid, call.message.chat.id)
    udata["warns"] = min(udata.get("warns", 0) + 1, 3)
    udata["violations"] = udata.get("violations", 0) + 1
    save_db(db)
    await call.answer(f'Предупреждение выдано! ({udata["warns"]}/3)', show_alert=True)
    await call.message.edit_reply_markup(reply_markup=None)

@router.message(F.text.regexp(r'(?i)^[!]пин$'))
async def cmd_pin(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_staff(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только персонал может закреплять.</b>', parse_mode=ParseMode.HTML)
        return
    if not message.reply_to_message:
        await message.reply(f'{E["warn"]} <b>Ответьте на сообщение для закрепления.</b>', parse_mode=ParseMode.HTML)
        return
    try:
        await message.bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
        await message.reply(f'{E["pin"]} <b>Сообщение закреплено.</b>', parse_mode=ParseMode.HTML)
    except TelegramBadRequest as e:
        await message.reply(f'{E["cross"]} Ошибка: {e}', parse_mode=ParseMode.HTML)

@router.message(F.text.regexp(r'(?i)^[!]откреп$'))
async def cmd_unpin(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_staff(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только персонал может откреплять.</b>', parse_mode=ParseMode.HTML)
        return
    try:
        await message.bot.unpin_all_chat_messages(message.chat.id)
        await message.reply(f'{E["check"]} <b>Все закреплённые сообщения откреплены.</b>', parse_mode=ParseMode.HTML)
    except:
        pass

@router.message(F.text.regexp(r'(?i)^[!]ссылка'))
async def cmd_invite(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_staff(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только персонал может создавать ссылки.</b>', parse_mode=ParseMode.HTML)
        return
    parts = message.text.split(maxsplit=1)
    label = parts[1] if len(parts) > 1 else "Инвайт"
    try:
        link = await message.bot.create_chat_invite_link(message.chat.id, name=label)
        await message.reply(
            f'{E["link"]} <b>Ссылка создана:</b>\n<a href="{link.invite_link}">{label}</a>',
            parse_mode=ParseMode.HTML
        )
    except TelegramBadRequest as e:
        await message.reply(f'{E["cross"]} Ошибка: {e}', parse_mode=ParseMode.HTML)

@router.message(F.text.regexp(r'(?i)^[!]модер'))
async def cmd_set_mod(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_admin(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только администраторы могут назначать модераторов.</b>', parse_mode=ParseMode.HTML)
        return
    if not message.reply_to_message:
        await message.reply(f'{E["warn"]} <b>Ответьте на сообщение пользователя.</b>', parse_mode=ParseMode.HTML)
        return
    target = message.reply_to_message.from_user
    group = get_group(db, message.chat.id)
    uid_str = str(target.id)
    if uid_str not in group["staff"]["mods"]:
        group["staff"]["mods"].append(uid_str)
    save_db(db)
    await message.reply(
        f'{E["check"]} {mention_html(target.full_name, target.id)} назначен(а) {E["profile"]} <b>Модератором</b>.',
        parse_mode=ParseMode.HTML
    )

@router.message(F.text.regexp(r'(?i)^[!]сеньор'))
async def cmd_set_senior(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if message.from_user.id != OWNER_ID:
        await message.reply(f'{E["cross"]} <b>Только владелец может назначать старших админов.</b>', parse_mode=ParseMode.HTML)
        return
    if not message.reply_to_message:
        await message.reply(f'{E["warn"]} <b>Ответьте на сообщение пользователя.</b>', parse_mode=ParseMode.HTML)
        return
    target = message.reply_to_message.from_user
    group = get_group(db, message.chat.id)
    uid_str = str(target.id)
    if uid_str not in group["staff"]["senior_admins"]:
        group["staff"]["senior_admins"].append(uid_str)
    save_db(db)
    await message.reply(
        f'{E["check"]} {mention_html(target.full_name, target.id)} назначен(а) {E["star"]} <b>Старшим админом</b>.',
        parse_mode=ParseMode.HTML
    )

@router.message(F.text.regexp(r'(?i)^[!]админ'))
async def cmd_set_admin(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if message.from_user.id != OWNER_ID:
        await message.reply(f'{E["cross"]} <b>Только владелец может назначать администраторов.</b>', parse_mode=ParseMode.HTML)
        return
    if not message.reply_to_message:
        await message.reply(f'{E["warn"]} <b>Ответьте на сообщение пользователя.</b>', parse_mode=ParseMode.HTML)
        return
    target = message.reply_to_message.from_user
    group = get_group(db, message.chat.id)
    uid_str = str(target.id)
    if uid_str not in group["staff"]["admins"]:
        group["staff"]["admins"].append(uid_str)
    save_db(db)
    await message.reply(
        f'{E["check"]} {mention_html(target.full_name, target.id)} назначен(а) {E["shield"]} <b>Администратором</b>.',
        parse_mode=ParseMode.HTML
    )

@router.message(F.text.regexp(r'(?i)^[!]деадмин$'))
async def cmd_deadmin(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if message.from_user.id != OWNER_ID:
        await message.reply(f'{E["cross"]} <b>Только владелец может снимать с должностей.</b>', parse_mode=ParseMode.HTML)
        return
    if not message.reply_to_message:
        await message.reply(f'{E["warn"]} <b>Ответьте на сообщение пользователя.</b>', parse_mode=ParseMode.HTML)
        return
    target = message.reply_to_message.from_user
    group = get_group(db, message.chat.id)
    uid_str = str(target.id)
    removed = False
    for role_key in ["senior_admins", "admins", "mods"]:
        if uid_str in group["staff"][role_key]:
            group["staff"][role_key].remove(uid_str)
            removed = True
    save_db(db)
    if removed:
        await message.reply(
            f'{E["trash"]} {mention_html(target.full_name, target.id)} снят(а) со всех должностей.',
            parse_mode=ParseMode.HTML
        )
    else:
        await message.reply(f'{E["info"]} Пользователь не является персоналом.', parse_mode=ParseMode.HTML)

@router.message(F.text.regexp(r'(?i)^[!]панель$'))
async def cmd_panel(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_admin(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только администраторы.</b>', parse_mode=ParseMode.HTML)
        return
    chat_id = message.chat.id
    group = get_group(db, chat_id)
    check_stats_date(group)
    total_today = sum(v.get("count", 0) for v in group["stats_today"].values())
    staff = group["staff"]
    total_staff = len(staff["admins"]) + len(staff["senior_admins"]) + len(staff["mods"])
    users_count = len([k for k in db["users"] if k.startswith(f"{chat_id}_")])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Настройки", icon_custom_emoji_id="5278602437001767574", callback_data="panel_settings"),
         InlineKeyboardButton(text="Персонал", icon_custom_emoji_id="5298668674532538341", callback_data="panel_staff")],
        [InlineKeyboardButton(text="Статистика", icon_custom_emoji_id="5278778882848220741", callback_data="panel_stats"),
         InlineKeyboardButton(text="Репутация", icon_custom_emoji_id="5276111746812112286", callback_data="panel_rep")],
        [InlineKeyboardButton(text="Наказания", icon_custom_emoji_id="5276240711795107620", callback_data="panel_punish"),
         InlineKeyboardButton(text="Правила", icon_custom_emoji_id="5206626000665868017", callback_data="panel_rules")],
        [InlineKeyboardButton(text="Цензура", icon_custom_emoji_id="5278578973595427038", callback_data="panel_censorship"),
         InlineKeyboardButton(text="Антиспам", icon_custom_emoji_id="5276240711795107620", callback_data="panel_antispam")],
        [InlineKeyboardButton(text="Закрыть", icon_custom_emoji_id="5278578973595427038", callback_data="close_msg")],
    ])
    save_db(db)
    await message.reply(
        f'{E["pc"]} <b>Панель управления группой</b>\n\n'
        f'{E["people"]} Участников в базе: <b>{users_count}</b>\n'
        f'{E["shield"]} Персонала: <b>{total_staff}</b>\n'
        f'{E["chart"]} Сообщений сегодня: <b>{total_today}</b>\n'
        f'{E["settings"]} Группа: <b>{message.chat.title}</b>',
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

@router.callback_query(F.data == "panel_settings")
async def panel_settings_cb(call: CallbackQuery):
    db = load_db()
    if not is_admin(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    group = get_group(db, call.message.chat.id)
    settings = group.get("settings", {})
    welcome = settings.get("welcome", True)
    antiflood = settings.get("antiflood", False)
    antilinks = settings.get("antilinks", False)
    antispam = settings.get("antispam", False)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=(eb("✅", "5278411813468269386") if welcome else eb("❌", "5278578973595427038")) + " Приветствие",
            callback_data="toggle_welcome"
        )],
        [InlineKeyboardButton(
            text=(eb("✅", "5278411813468269386") if antiflood else eb("❌", "5278578973595427038")) + " Антифлуд",
            callback_data="toggle_antiflood"
        )],
        [InlineKeyboardButton(
            text=(eb("✅", "5278411813468269386") if antilinks else eb("❌", "5278578973595427038")) + " Антиссылки",
            callback_data="toggle_antilinks"
        )],
        [InlineKeyboardButton(
            text=(eb("✅", "5278411813468269386") if antispam else eb("❌", "5278578973595427038")) + " Антиспам",
            callback_data="toggle_antispam"
        )],
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="panel_back")],
    ])
    await call.message.edit_text(
        f'{E["settings"]} <b>Настройки группы</b>',
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

@router.callback_query(F.data == "toggle_welcome")
async def toggle_welcome_cb(call: CallbackQuery):
    db = load_db()
    group = get_group(db, call.message.chat.id)
    group["settings"]["welcome"] = not group["settings"].get("welcome", True)
    save_db(db)
    await call.answer("Изменено!", show_alert=True)
    await panel_settings_cb(call)

@router.callback_query(F.data == "toggle_antiflood")
async def toggle_antiflood_cb(call: CallbackQuery):
    db = load_db()
    group = get_group(db, call.message.chat.id)
    group["settings"]["antiflood"] = not group["settings"].get("antiflood", False)
    save_db(db)
    await call.answer("Изменено!", show_alert=True)
    await panel_settings_cb(call)

@router.callback_query(F.data == "toggle_antilinks")
async def toggle_antilinks_cb(call: CallbackQuery):
    db = load_db()
    group = get_group(db, call.message.chat.id)
    group["settings"]["antilinks"] = not group["settings"].get("antilinks", False)
    save_db(db)
    await call.answer("Изменено!", show_alert=True)
    await panel_settings_cb(call)

@router.callback_query(F.data == "toggle_antispam")
async def toggle_antispam_cb(call: CallbackQuery):
    db = load_db()
    group = get_group(db, call.message.chat.id)
    group["settings"]["antispam"] = not group["settings"].get("antispam", False)
    save_db(db)
    await call.answer("Изменено!", show_alert=True)
    await panel_settings_cb(call)

@router.callback_query(F.data == "panel_censorship")
async def panel_censorship_cb(call: CallbackQuery):
    db = load_db()
    if not is_admin(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    group = get_group(db, call.message.chat.id)
    words = group.get("censorship", [])
    words_text = '\n'.join(f'<b>L</b> <code>{w}</code>' for w in words) if words else '<i>Список пуст</i>'
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить слова", icon_custom_emoji_id="5242329690135356589", callback_data="censor_add_prompt"),
         InlineKeyboardButton(text="Очистить всё", icon_custom_emoji_id="5276384644739129761", callback_data="censor_clear")],
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="panel_back")],
    ])
    await call.message.edit_text(
        f'{E["shield"]} <b>Цензура слов</b>\n\n'
        f'Бот молча удаляет сообщения с запрещёнными словами.\n\n'
        f'<b>Запрещённые слова ({len(words)}):</b>\n{words_text}\n\n'
        f'{E["info"]} Добавить через: <code>!цензура добавить слово1,слово2</code>',
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )
    await call.answer()

@router.callback_query(F.data == "censor_clear")
async def censor_clear_cb(call: CallbackQuery):
    db = load_db()
    if not is_admin(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    group = get_group(db, call.message.chat.id)
    group["censorship"] = []
    save_db(db)
    await call.answer("Список цензуры очищен!", show_alert=True)
    await panel_censorship_cb(call)

@router.callback_query(F.data == "censor_add_prompt")
async def censor_add_prompt_cb(call: CallbackQuery):
    await call.answer(
        "Напишите: !цензура добавить слово1,слово2,слово3",
        show_alert=True
    )

@router.callback_query(F.data == "panel_antispam")
async def panel_antispam_cb(call: CallbackQuery):
    db = load_db()
    if not is_admin(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    group = get_group(db, call.message.chat.id)
    antispam = group["settings"].get("antispam", False)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=(eb("✅", "5278411813468269386") if antispam else eb("❌", "5278578973595427038")) + " Антиспам",
            callback_data="toggle_antispam"
        )],
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="panel_back")],
    ])
    await call.message.edit_text(
        f'{E["shield"]} <b>Антиспам</b>\n\n'
        f'При включении бот удаляет одинаковые сообщения и спам стикерами.\n'
        f'Нарушитель получает предупреждение.\n\n'
        f'Лимит: <b>{SPAM_MSG_LIMIT}</b> одинаковых сообщений за <b>{SPAM_WINDOW}</b> сек.\n'
        f'Лимит стикеров: <b>{SPAM_STICKER_LIMIT}</b> за <b>{SPAM_WINDOW}</b> сек.',
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )
    await call.answer()

@router.callback_query(F.data == "panel_rep")
async def panel_rep_cb(call: CallbackQuery):
    db = load_db()
    if not is_admin(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    group = get_group(db, call.message.chat.id)
    daily_limit = group.get("rep_daily_limit", 5)
    cooldown = group.get("rep_cooldown_hours", 0.0)
    plus_count = len(group.get("rep_triggers_plus", []))
    minus_count = len(group.get("rep_triggers_minus", []))
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Триггеры повыше...", icon_custom_emoji_id="5242329690135356589", callback_data="rep_triggers_plus"),
         InlineKeyboardButton(text="Триггеры пониже...", icon_custom_emoji_id="5244796895443838315", callback_data="rep_triggers_minus")],
        [InlineKeyboardButton(text="Дневной лимит", icon_custom_emoji_id="5276412364458059956", callback_data="rep_set_limit"),
         InlineKeyboardButton(text="Кулдаун (часы)", icon_custom_emoji_id="5276412364458059956", callback_data="rep_set_cooldown")],
        [InlineKeyboardButton(text="Сбросить лимиты", icon_custom_emoji_id="5278611606756942667", callback_data="rep_reset_limits")],
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="panel_back")],
    ])
    await call.message.edit_text(
        f'{E["star"]} <b>Репутация участников</b>\n'
        f'<b>L</b> Дневной лимит оценок: <b>{daily_limit} реп.</b>\n'
        f'<b>L</b> Кулдаун на получателя: <b>{cooldown} ч.</b>\n'
        f'<b>L</b> Триггеров повышения: <b>{plus_count}</b>\n'
        f'<b>L</b> Триггеров понижения: <b>{minus_count}</b>',
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

@router.callback_query(F.data == "rep_triggers_plus")
async def rep_triggers_plus_cb(call: CallbackQuery):
    db = load_db()
    group = get_group(db, call.message.chat.id)
    triggers = group.get("rep_triggers_plus", [])
    lines = '\n'.join(f'<b>L</b> {t}' for t in triggers)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить", icon_custom_emoji_id="5242329690135356589", callback_data="rep_add_plus"),
         InlineKeyboardButton(text="Удалить", icon_custom_emoji_id="5276384644739129761", callback_data="rep_del_plus")],
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="panel_rep")],
    ])
    await call.message.edit_text(
        f'{E["star"]} <b>Триггеры повышения репутации</b>\n\nТекущие триггеры:\n{lines}',
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

@router.callback_query(F.data == "rep_triggers_minus")
async def rep_triggers_minus_cb(call: CallbackQuery):
    db = load_db()
    group = get_group(db, call.message.chat.id)
    triggers = group.get("rep_triggers_minus", [])
    lines = '\n'.join(f'<b>L</b> {t}' for t in triggers)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить", icon_custom_emoji_id="5242329690135356589", callback_data="rep_add_minus"),
         InlineKeyboardButton(text="Удалить", icon_custom_emoji_id="5276384644739129761", callback_data="rep_del_minus")],
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="panel_rep")],
    ])
    await call.message.edit_text(
        f'{E["minus"]} <b>Триггеры понижения репутации</b>\n\nТекущие триггеры:\n{lines}',
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

@router.callback_query(F.data == "rep_reset_limits")
async def rep_reset_limits_cb(call: CallbackQuery):
    db = load_db()
    if not is_admin(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    chat_id = call.message.chat.id
    for key, udata in db["users"].items():
        if udata.get("chat_id") == chat_id:
            udata["rep_given_today"] = {}
            udata["rep_received_today"] = 0
    save_db(db)
    await call.answer("Лимиты сброшены!", show_alert=True)

@router.callback_query(F.data == "panel_stats")
async def panel_stats_cb(call: CallbackQuery):
    db = load_db()
    chat_id = call.message.chat.id
    group = get_group(db, chat_id)
    check_stats_date(group)
    stats = group.get("stats_today", {})
    sorted_stats = sorted(stats.items(), key=lambda x: x[1].get("count", 0), reverse=True)[:10]
    lines = []
    for i, (uid_str, stat) in enumerate(sorted_stats, 1):
        count = stat.get("count", 0)
        name = stat.get("name", uid_str)
        lines.append(f'<b>{i}.</b> {mention_html(name, int(uid_str))} — <b>{count}</b>')
    save_db(db)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="panel_back")]
    ])
    text = f'{E["chart"]} <b>Статистика за сегодня:</b>\n\n' + ('\n'.join(lines) if lines else 'Нет данных')
    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

# ─── Staff wizard ────────────────────────────────────────────────────────────
# STAFF_WIZARD[chat_id][admin_uid] = {
#   "step": "awaiting_user" | "awaiting_title_new" | "awaiting_title_edit",
#   "msg_id": int,
#   "target_id": int | None,
#   "target_name": str | None,
#   "role_key": str | None,
# }
STAFF_WIZARD: dict[int, dict[int, dict]] = {}

ROLE_KEYS = ["senior_admins", "admins", "mods"]
ROLE_DEFAULTS = {"senior_admins": "Старший админ", "admins": "Администратор", "mods": "Модератор"}
ROLE_EMOJI_KEY = {"senior_admins": "star", "admins": "shield", "mods": "profile"}

def get_role_display_name(group: dict, role_key: str) -> str:
    return group.get("role_names", {}).get(role_key, ROLE_DEFAULTS.get(role_key, role_key))

def get_staff_title(group: dict, uid_str: str, role_key: str) -> str:
    return group.get("staff_titles", {}).get(uid_str) or get_role_display_name(group, role_key)

def get_user_role_key(group: dict, uid_str: str) -> str | None:
    for rk in ROLE_KEYS:
        if uid_str in group["staff"].get(rk, []):
            return rk
    return None

async def render_staff_panel(bot, chat_id: int, msg_id: int, db: dict):
    group = get_group(db, chat_id)
    staff = group["staff"]

    all_staff = []
    for rk in ROLE_KEYS:
        for uid_str in staff.get(rk, []):
            all_staff.append((uid_str, rk))

    if all_staff:
        lines = [f'{E["people"]} <b>Персонал группы</b>\n']
        kb_rows = []
        for uid_str, rk in all_staff:
            emoji = E[ROLE_EMOJI_KEY[rk]]
            title = get_staff_title(group, uid_str, rk)
            try:
                member = await bot.get_chat_member(chat_id, int(uid_str))
                name = member.user.full_name
                uname = f" @{member.user.username}" if member.user.username else ""
            except Exception:
                name = uid_str
                uname = ""
            lines.append(f'{emoji} <b>{name}</b>{uname} — <i>{title}</i>')
            kb_rows.append([InlineKeyboardButton(
                text=f"{name} — {title}",
                callback_data=f"smng|{uid_str}"
            )])
        text = '\n'.join(lines)
    else:
        text = f'{E["people"]} <b>Персонал группы</b>\n\n<i>Сотрудников пока нет</i>'
        kb_rows = []

    kb_rows.append([InlineKeyboardButton(
        text="Добавить сотрудника",
        icon_custom_emoji_id="5242329690135356589",
        callback_data="staff_new"
    )])
    kb_rows.append([InlineKeyboardButton(
        text="Назад",
        icon_custom_emoji_id="5206401524200145033",
        callback_data="panel_back"
    )])

    await bot.edit_message_text(
        text, chat_id=chat_id, message_id=msg_id,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows)
    )

async def render_panel_main(bot, chat_id: int, msg_id: int, db: dict, chat_title: str = "Группа"):
    group = get_group(db, chat_id)
    check_stats_date(group)
    total_today = sum(v.get("count", 0) for v in group["stats_today"].values())
    staff = group["staff"]
    total_staff = len(staff.get("admins", [])) + len(staff.get("senior_admins", [])) + len(staff.get("mods", []))
    users_count = len([k for k in db["users"] if k.startswith(f"{chat_id}_")])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Настройки", icon_custom_emoji_id="5278602437001767574", callback_data="panel_settings"),
         InlineKeyboardButton(text="Персонал", icon_custom_emoji_id="5298668674532538341", callback_data="panel_staff")],
        [InlineKeyboardButton(text="Статистика", icon_custom_emoji_id="5278778882848220741", callback_data="panel_stats"),
         InlineKeyboardButton(text="Репутация", icon_custom_emoji_id="5276111746812112286", callback_data="panel_rep")],
        [InlineKeyboardButton(text="Наказания", icon_custom_emoji_id="5276240711795107620", callback_data="panel_punish"),
         InlineKeyboardButton(text="Правила", icon_custom_emoji_id="5206626000665868017", callback_data="panel_rules")],
        [InlineKeyboardButton(text="Цензура", icon_custom_emoji_id="5278578973595427038", callback_data="panel_censorship"),
         InlineKeyboardButton(text="Антиспам", icon_custom_emoji_id="5276240711795107620", callback_data="panel_antispam")],
        [InlineKeyboardButton(text="Закрыть", icon_custom_emoji_id="5278578973595427038", callback_data="close_msg")],
    ])
    await bot.edit_message_text(
        f'{E["pc"]} <b>Панель управления группой</b>\n\n'
        f'{E["people"]} Участников в базе: <b>{users_count}</b>\n'
        f'{E["shield"]} Персонала: <b>{total_staff}</b>\n'
        f'{E["chart"]} Сообщений сегодня: <b>{total_today}</b>\n'
        f'{E["settings"]} Группа: <b>{chat_title}</b>',
        chat_id=chat_id, message_id=msg_id,
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

@router.callback_query(F.data == "panel_staff")
async def panel_staff_cb(call: CallbackQuery):
    db = load_db()
    if not is_admin(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    await render_staff_panel(call.bot, call.message.chat.id, call.message.message_id, db)
    await call.answer()

@router.callback_query(F.data == "panel_back")
async def panel_back_cb(call: CallbackQuery):
    db = load_db()
    if not is_admin(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    save_db(db)
    try:
        await render_panel_main(call.bot, call.message.chat.id, call.message.message_id, db, call.message.chat.title or "Группа")
    except Exception:
        pass
    await call.answer()

# ── Wizard: добавить нового сотрудника ──────────────────────────────────────

@router.callback_query(F.data == "staff_new")
async def staff_new_cb(call: CallbackQuery):
    db = load_db()
    if not is_admin(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    chat_id = call.message.chat.id
    admin_uid = call.from_user.id
    STAFF_WIZARD.setdefault(chat_id, {})[admin_uid] = {
        "step": "awaiting_user",
        "msg_id": call.message.message_id,
        "target_id": None,
        "target_name": None,
        "role_key": None,
    }
    await call.message.edit_text(
        f'{E["pencil"]} <b>Добавление сотрудника</b>\n\n'
        f'<b>Шаг 1 из 3</b> — Напишите <b>@username</b> или числовой <b>ID</b> пользователя в этот чат.',
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", icon_custom_emoji_id="5278578973595427038", callback_data="staff_wiz_cancel")]
        ])
    )
    await call.answer()

@router.callback_query(F.data.startswith("swrole|"))
async def staff_wiz_role_cb(call: CallbackQuery):
    """Шаг 2: выбор должности для нового сотрудника."""
    db = load_db()
    if not is_admin(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    parts = call.data.split("|")
    role_key = parts[1]
    target_id = int(parts[2])
    chat_id = call.message.chat.id
    admin_uid = call.from_user.id
    wiz = STAFF_WIZARD.get(chat_id, {}).get(admin_uid)
    if not wiz:
        await call.answer("Сессия истекла. Начните заново.", show_alert=True)
        return
    wiz["role_key"] = role_key
    wiz["step"] = "awaiting_title_new"
    db2 = load_db()
    group = get_group(db2, chat_id)
    role_name = get_role_display_name(group, role_key)
    target_name = wiz["target_name"] or str(target_id)
    await call.message.edit_text(
        f'{E["pencil"]} <b>Добавление сотрудника</b>\n\n'
        f'Пользователь: <b>{target_name}</b>\n'
        f'Должность: <b>{role_name}</b>\n\n'
        f'<b>Шаг 3 из 3</b> — Введите <b>звание</b> для сотрудника\n'
        f'<i>(например: «Куратор», «Хэлпер», «Куйн»)</i>\n\n'
        f'Или нажмите «Без звания» чтобы оставить стандартное.',
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Без звания", callback_data=f"swnotitle|{role_key}|{target_id}")],
            [InlineKeyboardButton(text="Отмена", icon_custom_emoji_id="5278578973595427038", callback_data="staff_wiz_cancel")]
        ])
    )
    await call.answer()

@router.callback_query(F.data.startswith("swnotitle|"))
async def staff_wiz_notitle_cb(call: CallbackQuery):
    """Добавить без кастомного звания."""
    db = load_db()
    if not is_admin(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    parts = call.data.split("|")
    role_key = parts[1]
    target_id = int(parts[2])
    chat_id = call.message.chat.id
    admin_uid = call.from_user.id
    wiz = STAFF_WIZARD.get(chat_id, {}).pop(admin_uid, {})
    target_name = wiz.get("target_name") or str(target_id)
    group = get_group(db, chat_id)
    uid_str = str(target_id)
    for rk in ROLE_KEYS:
        if uid_str in group["staff"].get(rk, []):
            group["staff"][rk].remove(uid_str)
    group["staff"].setdefault(role_key, [])
    if uid_str not in group["staff"][role_key]:
        group["staff"][role_key].append(uid_str)
    group.get("staff_titles", {}).pop(uid_str, None)
    save_db(db)
    role_name = get_role_display_name(group, role_key)
    await call.answer(f"✅ {target_name} добавлен как {role_name}!", show_alert=True)
    await render_staff_panel(call.bot, chat_id, call.message.message_id, db)

@router.callback_query(F.data == "staff_wiz_cancel")
async def staff_wiz_cancel_cb(call: CallbackQuery):
    chat_id = call.message.chat.id
    STAFF_WIZARD.get(chat_id, {}).pop(call.from_user.id, None)
    db = load_db()
    await render_staff_panel(call.bot, chat_id, call.message.message_id, db)
    await call.answer()

# ── Управление конкретным сотрудником ───────────────────────────────────────

@router.callback_query(F.data.startswith("smng|"))
async def staff_manage_cb(call: CallbackQuery):
    db = load_db()
    if not is_admin(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    uid_str = call.data[5:]
    chat_id = call.message.chat.id
    group = get_group(db, chat_id)
    role_key = get_user_role_key(group, uid_str)
    if not role_key:
        await call.answer("Сотрудник не найден", show_alert=True)
        return
    emoji = E[ROLE_EMOJI_KEY[role_key]]
    role_name = get_role_display_name(group, role_key)
    title = get_staff_title(group, uid_str, role_key)
    try:
        member = await call.bot.get_chat_member(chat_id, int(uid_str))
        name = member.user.full_name
        uname = f"@{member.user.username}" if member.user.username else "нет"
    except Exception:
        name = uid_str
        uname = "нет"
    text = (
        f'{emoji} <b>{name}</b>\n\n'
        f'{E["profile"]} Username: {uname}\n'
        f'{E["info"]} ID: <code>{uid_str}</code>\n'
        f'{E["shield"]} Должность: <b>{role_name}</b>\n'
        f'{E["star"]} Звание: <b>{title}</b>'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить роль", icon_custom_emoji_id="5278611606756942667", callback_data=f"smrole|{uid_str}"),
         InlineKeyboardButton(text="Изменить звание", icon_custom_emoji_id="5276442772826515132", callback_data=f"smtitle|{uid_str}")],
        [InlineKeyboardButton(text="Снять с должности", icon_custom_emoji_id="5278578973595427038", callback_data=f"smfire|{uid_str}")],
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="panel_staff")],
    ])
    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    await call.answer()

@router.callback_query(F.data.startswith("smrole|"))
async def staff_manage_role_cb(call: CallbackQuery):
    db = load_db()
    if not is_admin(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    uid_str = call.data[7:]
    chat_id = call.message.chat.id
    group = get_group(db, chat_id)
    try:
        member = await call.bot.get_chat_member(chat_id, int(uid_str))
        name = member.user.full_name
    except Exception:
        name = uid_str
    kb_rows = []
    for rk in ROLE_KEYS:
        rname = get_role_display_name(group, rk)
        kb_rows.append([InlineKeyboardButton(text=rname, callback_data=f"smrole_set|{rk}|{uid_str}")])
    kb_rows.append([InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data=f"smng|{uid_str}")])
    await call.message.edit_text(
        f'{E["shield"]} <b>Изменить роль — {name}</b>\n\nВыберите новую должность:',
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows)
    )
    await call.answer()

@router.callback_query(F.data.startswith("smrole_set|"))
async def staff_manage_role_set_cb(call: CallbackQuery):
    db = load_db()
    if not is_admin(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    parts = call.data.split("|")
    role_key = parts[1]
    uid_str = parts[2]
    chat_id = call.message.chat.id
    group = get_group(db, chat_id)
    for rk in ROLE_KEYS:
        if uid_str in group["staff"].get(rk, []):
            group["staff"][rk].remove(uid_str)
    group["staff"].setdefault(role_key, [])
    if uid_str not in group["staff"][role_key]:
        group["staff"][role_key].append(uid_str)
    save_db(db)
    role_name = get_role_display_name(group, role_key)
    await call.answer(f"Роль изменена на {role_name}!", show_alert=True)
    await render_staff_panel(call.bot, chat_id, call.message.message_id, db)

@router.callback_query(F.data.startswith("smtitle|"))
async def staff_manage_title_cb(call: CallbackQuery):
    db = load_db()
    if not is_admin(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    uid_str = call.data[8:]
    chat_id = call.message.chat.id
    admin_uid = call.from_user.id
    group = get_group(db, chat_id)
    rk = get_user_role_key(group, uid_str)
    try:
        member = await call.bot.get_chat_member(chat_id, int(uid_str))
        name = member.user.full_name
    except Exception:
        name = uid_str
    current_title = get_staff_title(group, uid_str, rk or "mods")
    STAFF_WIZARD.setdefault(chat_id, {})[admin_uid] = {
        "step": "awaiting_title_edit",
        "msg_id": call.message.message_id,
        "target_id": int(uid_str),
        "target_name": name,
        "role_key": rk,
    }
    await call.message.edit_text(
        f'{E["pencil"]} <b>Изменить звание — {name}</b>\n\n'
        f'Текущее: <b>{current_title}</b>\n\n'
        f'Напишите новое звание в чат:',
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Сбросить (вернуть стандартное)", callback_data=f"smtitle_reset|{uid_str}")],
            [InlineKeyboardButton(text="Отмена", icon_custom_emoji_id="5278578973595427038", callback_data="staff_wiz_cancel")]
        ])
    )
    await call.answer()

@router.callback_query(F.data.startswith("smtitle_reset|"))
async def staff_title_reset_cb(call: CallbackQuery):
    db = load_db()
    uid_str = call.data[14:]
    chat_id = call.message.chat.id
    STAFF_WIZARD.get(chat_id, {}).pop(call.from_user.id, None)
    group = get_group(db, chat_id)
    group.setdefault("staff_titles", {}).pop(uid_str, None)
    save_db(db)
    await call.answer("Звание сброшено!", show_alert=True)
    await render_staff_panel(call.bot, chat_id, call.message.message_id, db)

@router.callback_query(F.data.startswith("smfire|"))
async def staff_fire_cb(call: CallbackQuery):
    db = load_db()
    if not is_admin(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    uid_str = call.data[7:]
    chat_id = call.message.chat.id
    group = get_group(db, chat_id)
    removed = False
    for rk in ROLE_KEYS:
        if uid_str in group["staff"].get(rk, []):
            group["staff"][rk].remove(uid_str)
            removed = True
    group.get("staff_titles", {}).pop(uid_str, None)
    save_db(db)
    await call.answer("Снят с должности!" if removed else "Не найден", show_alert=True)
    await render_staff_panel(call.bot, chat_id, call.message.message_id, db)


@router.callback_query(F.data == "panel_rules")
async def panel_rules_cb(call: CallbackQuery):
    db = load_db()
    if not is_admin(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить правила", icon_custom_emoji_id="5276442772826515132", callback_data="edit_rules")],
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="panel_back")],
    ])
    await call.message.edit_text(
        f'{E["book"]} <b>Управление правилами</b>\n\nОтправьте <code>!сетправила [текст]</code> для обновления или нажмите кнопку ниже.',
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

@router.callback_query(F.data == "edit_rules")
async def edit_rules_cb(call: CallbackQuery, state: FSMContext):
    db = load_db()
    if not is_admin(db, call.from_user.id, call.message.chat.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    await state.update_data(chat_id=call.message.chat.id, msg_id=call.message.message_id)
    await state.set_state(RulesFSM.waiting_text)
    await call.message.edit_text(
        f'{E["pencil"]} <b>Изменение правил</b>\n\nНапишите новый текст правил в чат:',
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", icon_custom_emoji_id="5278578973595427038", callback_data="rules_fsm_cancel")]
        ])
    )
    await call.answer()

@router.callback_query(F.data == "rules_fsm_cancel")
async def rules_fsm_cancel_cb(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await panel_rules_cb(call)

@router.message(RulesFSM.waiting_text)
async def rules_fsm_text(message: Message, state: FSMContext):
    data = await state.get_data()
    chat_id = data.get("chat_id")
    if not chat_id or message.chat.id != chat_id:
        return
    db = load_db()
    if not is_admin(db, message.from_user.id, chat_id):
        await state.clear()
        return
    group = get_group(db, chat_id)
    group["rules"] = message.text
    save_db(db)
    await state.clear()
    try:
        await message.delete()
    except:
        pass
    await message.answer(f'{E["check"]} <b>Правила обновлены!</b>', parse_mode=ParseMode.HTML)

@router.callback_query(F.data == "panel_punish")
async def panel_punish_cb(call: CallbackQuery):
    db = load_db()
    chat_id = call.message.chat.id
    banned_count = sum(1 for k, v in db["users"].items() if v.get("chat_id") == chat_id and v.get("banned"))
    muted_count = sum(1 for k, v in db["users"].items() if v.get("chat_id") == chat_id and v.get("muted_until"))
    warned_count = sum(1 for k, v in db["users"].items() if v.get("chat_id") == chat_id and v.get("warns", 0) > 0)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="panel_back")]
    ])
    await call.message.edit_text(
        f'{E["warn"]} <b>Активные наказания</b>\n\n'
        f'{E["lock"]} Заблокированных: <b>{banned_count}</b>\n'
        f'{E["clock"]} Замученных: <b>{muted_count}</b>\n'
        f'{E["excl"]} С предупреждениями: <b>{warned_count}</b>',
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

@router.message(F.text.regexp(r'(?i)^[!]настройки$'))
async def cmd_settings(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_admin(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только администраторы.</b>', parse_mode=ParseMode.HTML)
        return
    group = get_group(db, message.chat.id)
    settings = group.get("settings", {})
    welcome = settings.get("welcome", True)
    antiflood = settings.get("antiflood", False)
    antilinks = settings.get("antilinks", False)
    captcha = settings.get("captcha", False)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=(eb("✅", "5278411813468269386") if welcome else eb("❌", "5278578973595427038")) + " Приветствие",
            callback_data="toggle_welcome"
        )],
        [InlineKeyboardButton(
            text=(eb("✅", "5278411813468269386") if antiflood else eb("❌", "5278578973595427038")) + " Антифлуд",
            callback_data="toggle_antiflood"
        )],
        [InlineKeyboardButton(
            text=(eb("✅", "5278411813468269386") if antilinks else eb("❌", "5278578973595427038")) + " Антиссылки",
            callback_data="toggle_antilinks"
        )],
        [InlineKeyboardButton(
            text=(eb("✅", "5278411813468269386") if captcha else eb("❌", "5278578973595427038")) + " Капча",
            callback_data="toggle_captcha"
        )],
        [InlineKeyboardButton(text="Закрыть", icon_custom_emoji_id="5278578973595427038", callback_data="close_msg")],
    ])
    await message.reply(
        f'{E["settings"]} <b>Настройки группы</b>',
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

@router.callback_query(F.data == "toggle_captcha")
async def toggle_captcha_cb(call: CallbackQuery):
    db = load_db()
    group = get_group(db, call.message.chat.id)
    group["settings"]["captcha"] = not group["settings"].get("captcha", False)
    save_db(db)
    await call.answer("Изменено!", show_alert=True)

@router.message(F.text.regexp(r'(?i)^[!]сетправила'))
async def cmd_set_rules(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_admin(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только администраторы.</b>', parse_mode=ParseMode.HTML)
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply(f'{E["warn"]} <b>Укажите текст правил.</b>', parse_mode=ParseMode.HTML)
        return
    group = get_group(db, message.chat.id)
    group["rules"] = parts[1]
    save_db(db)
    await message.reply(f'{E["check"]} <b>Правила обновлены.</b>', parse_mode=ParseMode.HTML)

@router.message(F.text.regexp(r'(?i)^[!]чистка'))
async def cmd_purge(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_admin(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только администраторы.</b>', parse_mode=ParseMode.HTML)
        return
    parts = message.text.split()
    count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
    count = min(count, 100)
    deleted = 0
    # Удаляем само сообщение-команду + count предыдущих
    start_id = message.message_id
    try:
        for i in range(start_id, start_id - count - 1, -1):
            try:
                await message.bot.delete_message(message.chat.id, i)
                deleted += 1
            except:
                pass
    except:
        pass
    info = await message.answer(f'{E["trash"]} <b>Удалено {deleted} сообщений.</b>', parse_mode=ParseMode.HTML)
    await asyncio.sleep(3)
    try:
        await info.delete()
    except:
        pass

@router.message(F.text.regexp(r'(?i)^[!]гбан'))
async def cmd_gban(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    if not message.reply_to_message:
        await message.reply(f'{E["warn"]} <b>Ответьте на сообщение.</b>', parse_mode=ParseMode.HTML)
        return
    target = message.reply_to_message.from_user
    db = load_db()
    db["global_bans"][str(target.id)] = {"name": target.full_name, "date": str(date.today())}
    save_db(db)
    await message.reply(
        f'{E["lock"]} {mention_html(target.full_name, target.id)} добавлен в <b>глобальный бан</b>.',
        parse_mode=ParseMode.HTML
    )

@router.message(F.text.regexp(r'(?i)^[!]разгбан'))
async def cmd_ungban(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    if not message.reply_to_message:
        await message.reply(f'{E["warn"]} <b>Ответьте на сообщение.</b>', parse_mode=ParseMode.HTML)
        return
    target = message.reply_to_message.from_user
    db = load_db()
    if str(target.id) in db["global_bans"]:
        del db["global_bans"][str(target.id)]
    save_db(db)
    await message.reply(
        f'{E["unlock"]} {mention_html(target.full_name, target.id)} удалён из глобального бана.',
        parse_mode=ParseMode.HTML
    )

@router.message(F.text.regexp(r'(?i)^[!]кто$'))
async def cmd_who(message: Message):
    if not await check_access_info(message):
        return
    if not message.reply_to_message:
        await message.reply(f'{E["warn"]} <b>Ответьте на сообщение пользователя.</b>', parse_mode=ParseMode.HTML)
        return
    target = message.reply_to_message.from_user
    db = load_db()
    udata = get_user(db, target.id, message.chat.id)
    role = get_role_label(db, target.id, message.chat.id)
    rep = udata.get("reputation", 0)
    group = get_group(db, message.chat.id)
    title = get_rep_title(rep, group)
    await message.reply(
        f'{E["profile"]} <b>{target.full_name}</b>\n'
        f'<b>L</b> Роль: {role}\n'
        f'<b>L</b> Репутация: <b>{rep}</b> — {title}',
        parse_mode=ParseMode.HTML
    )

@router.message(F.text.regexp(r'(?i)^[!]правила$'))
async def cmd_rules_alias(message: Message):
    await cmd_rules(message)

@router.message(F.text.regexp(r'(?i)^[!]обо мне$'))
async def cmd_about_me(message: Message):
    if not await check_access_info(message):
        return
    target = message.from_user
    db = load_db()
    udata = get_user(db, target.id, message.chat.id)
    rep = udata.get("reputation", 0)
    warns = udata.get("warns", 0)
    group = get_group(db, message.chat.id)
    title = get_rep_title(rep, group)
    role = get_role_label(db, target.id, message.chat.id)
    await message.reply(
        f'{E["profile"]} <b>Ваш профиль</b>\n\n'
        f'<b>L</b> Имя: {mention_html(target.full_name, target.id)}\n'
        f'<b>L</b> ID: <code>{target.id}</code>\n'
        f'<b>L</b> Роль: {role}\n'
        f'<b>L</b> Репутация: <b>{rep}</b> — {title}\n'
        f'<b>L</b> Предупреждения: <b>{warns}/3</b>',
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data == "owner_stats")
async def owner_stats_cb(call: CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Нет доступа", show_alert=True)
        return
    db = load_db()
    total_groups = len(db.get("groups", {}))
    total_users = len(db.get("users", {}))
    total_bans = len(db.get("global_bans", {}))
    total_approved = len(db.get("approved_owners", []))
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="owner_back")]
    ])
    await call.message.edit_text(
        f'{E["chart"]} <b>Глобальная статистика</b>\n\n'
        f'{E["home"]} Групп: <b>{total_groups}</b>\n'
        f'{E["people"]} Пользователей: <b>{total_users}</b>\n'
        f'{E["lock"]} Глобальных банов: <b>{total_bans}</b>\n'
        f'{E["check"]} Одобренных владельцев: <b>{total_approved}</b>',
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

@router.callback_query(F.data == "owner_groups")
async def owner_groups_cb(call: CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Нет доступа", show_alert=True)
        return
    db = load_db()
    groups = db.get("groups", {})
    lines = []
    for gid, gdata in list(groups.items())[:20]:
        users_count = len([k for k in db["users"] if k.startswith(f"{gid}_")])
        lines.append(f'<b>L</b> <code>{gid}</code> — <b>{users_count}</b> пользователей')
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="owner_back")]
    ])
    text = f'{E["home"]} <b>Подключённые группы ({len(groups)})</b>\n\n' + ('\n'.join(lines) if lines else 'Нет групп')
    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

@router.callback_query(F.data == "owner_gbans")
async def owner_gbans_cb(call: CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Нет доступа", show_alert=True)
        return
    db = load_db()
    gbans = db.get("global_bans", {})
    lines = []
    for uid_str, data in list(gbans.items())[:20]:
        name = data.get("name", uid_str)
        lines.append(f'<b>L</b> {mention_html(name, int(uid_str))} [<code>{uid_str}</code>]')
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="owner_back")]
    ])
    text = f'{E["lock"]} <b>Глобальные баны ({len(gbans)})</b>\n\n' + ('\n'.join(lines) if lines else 'Список пуст')
    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

@router.callback_query(F.data == "owner_approvals")
async def owner_approvals_cb(call: CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Нет доступа", show_alert=True)
        return
    db = load_db()
    pending = db.get("pending_approval", [])
    lines = [f'<b>L</b> <code>{uid}</code>' for uid in pending]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="owner_back")]
    ])
    text = f'{E["bell"]} <b>Ожидают одобрения ({len(pending)})</b>\n\n' + ('\n'.join(lines) if lines else 'Нет заявок')
    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

@router.callback_query(F.data == "owner_back")
async def owner_back_cb(call: CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Нет доступа", show_alert=True)
        return
    db = load_db()
    groups = db.get("groups", {})
    total_groups = len(groups)
    total_users = len(db.get("users", {}))
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Статистика", icon_custom_emoji_id="5278778882848220741", callback_data="owner_stats"),
         InlineKeyboardButton(text="Группы", icon_custom_emoji_id="5298668674532538341", callback_data="owner_groups")],
        [InlineKeyboardButton(text="Глобальные баны", icon_custom_emoji_id="5278578973595427038", callback_data="owner_gbans"),
         InlineKeyboardButton(text="Одобрения", icon_custom_emoji_id="5278411813468269386", callback_data="owner_approvals")],
        [InlineKeyboardButton(text="Рассылка", icon_custom_emoji_id="5278528159837348960", callback_data="owner_broadcast")],
    ])
    await call.message.edit_text(
        f'{E["crown"]} <b>Панель владельца</b>\n\n'
        f'{E["people"]} Групп: <b>{total_groups}</b>\n'
        f'{E["profile"]} Пользователей: <b>{total_users}</b>',
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

@router.callback_query(F.data == "owner_broadcast")
async def owner_broadcast_cb(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != OWNER_ID:
        await call.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(BroadcastFSM.waiting_text)
    await call.message.edit_text(
        f'{E["mega"]} <b>Глобальная рассылка</b>\n\n'
        f'Напишите текст рассылки. Он будет отправлен во все группы.\n\n'
        f'<i>Поддерживается HTML-форматирование.</i>',
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", icon_custom_emoji_id="5278578973595427038", callback_data="broadcast_cancel")]
        ])
    )
    await call.answer()

@router.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancel_cb(call: CallbackQuery, state: FSMContext):
    await state.clear()
    db = load_db()
    total_groups = len(db.get("groups", {}))
    total_users = len(db.get("users", {}))
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Статистика", icon_custom_emoji_id="5278778882848220741", callback_data="owner_stats"),
         InlineKeyboardButton(text="Группы", icon_custom_emoji_id="5298668674532538341", callback_data="owner_groups")],
        [InlineKeyboardButton(text="Глобальные баны", icon_custom_emoji_id="5278578973595427038", callback_data="owner_gbans"),
         InlineKeyboardButton(text="Одобрения", icon_custom_emoji_id="5278411813468269386", callback_data="owner_approvals")],
        [InlineKeyboardButton(text="Рассылка", icon_custom_emoji_id="5278528159837348960", callback_data="owner_broadcast")],
    ])
    await call.message.edit_text(
        f'{E["crown"]} <b>Панель владельца</b>\n\n'
        f'{E["people"]} Групп: <b>{total_groups}</b>\n'
        f'{E["profile"]} Пользователей: <b>{total_users}</b>',
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )
    await call.answer()

@router.message(BroadcastFSM.waiting_text)
async def broadcast_fsm_text(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await state.clear()
    text = message.text or message.caption or ""
    if not text:
        await message.reply(f'{E["warn"]} Пустой текст. Рассылка отменена.')
        return
    db = load_db()
    groups = db.get("groups", {})
    sent = 0
    for gid in groups:
        try:
            await message.bot.send_message(int(gid), text, parse_mode=ParseMode.HTML)
            sent += 1
        except:
            pass
    await message.reply(f'{E["check"]} Рассылка отправлена в <b>{sent}</b> групп.', parse_mode=ParseMode.HTML)

@router.message(F.text.regexp(r'(?i)^[!]рассылка'))
async def cmd_broadcast(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply(f'{E["warn"]} Укажите текст рассылки.', parse_mode=ParseMode.HTML)
        return
    text = parts[1]
    db = load_db()
    groups = db.get("groups", {})
    sent = 0
    for gid in groups:
        try:
            await message.bot.send_message(int(gid), text, parse_mode=ParseMode.HTML)
            sent += 1
        except:
            pass
    await message.reply(f'{E["check"]} Рассылка отправлена в <b>{sent}</b> групп.', parse_mode=ParseMode.HTML)

@router.message(F.text.regexp(r'(?i)^[!]грассылка'))
async def cmd_group_broadcast(message: Message):
    """Рассылка внутри текущей группы."""
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_admin(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} Только администраторы.', parse_mode=ParseMode.HTML)
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply(f'{E["warn"]} Использование: <code>!грассылка [текст]</code>', parse_mode=ParseMode.HTML)
        return
    text = parts[1]
    try:
        await message.delete()
    except:
        pass
    await message.answer(text, parse_mode=ParseMode.HTML)

@router.message(F.text.regexp(r'(?i)^[!]статус'))
async def cmd_status(message: Message):
    if not await check_access_info(message):
        return
    db = load_db()
    group = get_group(db, message.chat.id)
    settings = group.get("settings", {})
    lines = []
    for key, label in [("welcome", "Приветствие"), ("antiflood", "Антифлуд"), ("antilinks", "Антиссылки"), ("captcha", "Капча"), ("antispam", "Антиспам")]:
        val = settings.get(key, False)
        icon = E["check"] if val else E["cross"]
        lines.append(f'{icon} {label}')
    censorship = group.get("censorship", [])
    lines.append(f'{E["shield"]} Цензура: <b>{len(censorship)} слов</b>')
    await message.reply(
        f'{E["info"]} <b>Статус функций группы</b>\n\n' + '\n'.join(lines),
        parse_mode=ParseMode.HTML
    )

@router.message(F.text.regexp(r'(?i)^[!]мои варны$'))
async def cmd_my_warns(message: Message):
    if not await check_access_info(message):
        return
    db = load_db()
    udata = get_user(db, message.from_user.id, message.chat.id)
    warns = udata.get("warns", 0)
    await message.reply(
        f'{E["warn"]} <b>Ваши предупреждения:</b> <b>{warns}/3</b>',
        parse_mode=ParseMode.HTML
    )

@router.message(F.text.regexp(r'(?i)^[!]чат$'))
async def cmd_chat_info(message: Message):
    if not await check_access_info(message):
        return
    chat = message.chat
    db = load_db()
    group = get_group(db, chat.id)
    staff = group["staff"]
    total_staff = len(staff["admins"]) + len(staff["senior_admins"]) + len(staff["mods"])
    try:
        count = await message.bot.get_chat_member_count(chat.id)
    except:
        count = "?"
    await message.reply(
        f'{E["home"]} <b>Информация о чате</b>\n\n'
        f'{E["info"]} Название: <b>{chat.title}</b>\n'
        f'{E["profile"]} ID: <code>{chat.id}</code>\n'
        f'{E["people"]} Участников: <b>{count}</b>\n'
        f'{E["shield"]} Персонала: <b>{total_staff}</b>',
        parse_mode=ParseMode.HTML
    )

@router.message(F.text.regexp(r'(?i)^[!]тихий'))
async def cmd_silent_mute(message: Message):
    """Тихий мут — без сообщения о наказании."""
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_staff(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только персонал может мутить.</b>', parse_mode=ParseMode.HTML)
        return
    if not message.reply_to_message:
        await message.reply(f'{E["warn"]} <b>Ответьте на сообщение пользователя.</b>', parse_mode=ParseMode.HTML)
        return
    target = message.reply_to_message.from_user
    if target.id == OWNER_ID:
        await message.reply(f'{E["cross"]} <b>Нельзя мутить владельца.</b>', parse_mode=ParseMode.HTML)
        return
    parts = message.text.split(maxsplit=1)
    args = parts[1] if len(parts) > 1 else ''
    duration_sec = parse_mute_duration(args) or 3600
    until = datetime.now() + timedelta(seconds=duration_sec)
    try:
        await message.bot.restrict_chat_member(
            message.chat.id, target.id,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_send_audios=False,
                can_send_documents=False,
                can_send_photos=False,
                can_send_videos=False,
                can_send_video_notes=False,
                can_send_voice_notes=False,
                can_send_polls=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False,
            ),
            until_date=until
        )
    except TelegramBadRequest:
        return
    udata = get_user(db, target.id, message.chat.id)
    udata["muted_until"] = until.strftime("%Y-%m-%d %H:%M")
    udata["violations"] = udata.get("violations", 0) + 1
    save_db(db)
    try:
        await message.delete()
    except:
        pass

@router.message(F.text.regexp(r'(?i)^[!]история$'))
async def cmd_history(message: Message):
    """История нарушений пользователя."""
    if not await check_access_info(message):
        return
    db = load_db()
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    else:
        target = message.from_user
    udata = get_user(db, target.id, message.chat.id)
    warns = udata.get("warns", 0)
    violations = udata.get("violations", 0)
    muted_until = udata.get("muted_until")
    banned = udata.get("banned", False)
    join_date = udata.get("join_date", "неизвестно")
    rep = udata.get("reputation", 0)
    role = get_role_label(db, target.id, message.chat.id)
    lines = []
    if banned:
        lines.append(f'{E["lock"]} Текущий статус: <b>Заблокирован</b>')
    if muted_until:
        lines.append(f'{E["clock"]} Мут до: <b>{muted_until}</b>')
    if warns > 0:
        lines.append(f'{E["warn"]} Активных предупреждений: <b>{warns}/3</b>')
    history_text = '\n'.join(lines) if lines else f'{E["check"]} Активных наказаний нет'
    await message.reply(
        f'{E["book"]} <b>История нарушений — {mention_html(target.full_name, target.id)}</b>\n\n'
        f'<blockquote><b>Профиль</b>\n'
        f'<b>L</b> Роль: {role}\n'
        f'<b>L</b> Репутация: <b>{rep}</b>\n'
        f'<b>L</b> В базе с: <b>{join_date}</b></blockquote>\n\n'
        f'<blockquote><b>Статистика нарушений</b>\n'
        f'<b>L</b> Всего нарушений: <b>{violations}</b>\n'
        f'<b>L</b> Активных варнов: <b>{warns}/3</b></blockquote>\n\n'
        f'<blockquote><b>Активные наказания</b>\n{history_text}</blockquote>',
        parse_mode=ParseMode.HTML
    )

@router.message(F.text.regexp(r'(?i)^[!]цензура'))
async def cmd_censorship_cmd(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_admin(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только администраторы.</b>', parse_mode=ParseMode.HTML)
        return
    parts = message.text.split(maxsplit=2)
    sub = parts[1].lower() if len(parts) > 1 else ''
    group = get_group(db, message.chat.id)

    if sub == 'добавить':
        if len(parts) < 3:
            await message.reply(f'{E["warn"]} Укажите слова через запятую:\n<code>!цензура добавить слово1,слово2</code>', parse_mode=ParseMode.HTML)
            return
        words = [w.strip().lower() for w in parts[2].split(',') if w.strip()]
        added = [w for w in words if w not in group["censorship"]]
        for w in added:
            group["censorship"].append(w)
        save_db(db)
        await message.reply(f'{E["check"]} Добавлено в цензуру: <b>{", ".join(added)}</b>\nВсего слов: <b>{len(group["censorship"])}</b>', parse_mode=ParseMode.HTML)

    elif sub == 'удалить':
        if len(parts) < 3:
            await message.reply(f'{E["warn"]} Укажите слово: <code>!цензура удалить слово</code>', parse_mode=ParseMode.HTML)
            return
        word = parts[2].lower().strip()
        if word in group["censorship"]:
            group["censorship"].remove(word)
            save_db(db)
            await message.reply(f'{E["check"]} Удалено из цензуры: <b>{word}</b>', parse_mode=ParseMode.HTML)
        else:
            await message.reply(f'{E["cross"]} Слово <b>{word}</b> не найдено в цензуре.', parse_mode=ParseMode.HTML)

    elif sub == 'список':
        words = group.get("censorship", [])
        if not words:
            await message.reply(f'{E["info"]} Список цензуры пуст.', parse_mode=ParseMode.HTML)
        else:
            lines = '\n'.join(f'<b>L</b> <code>{w}</code>' for w in words)
            await message.reply(f'{E["shield"]} <b>Запрещённые слова ({len(words)}):</b>\n{lines}', parse_mode=ParseMode.HTML)

    elif sub == 'очистить':
        group["censorship"] = []
        save_db(db)
        await message.reply(f'{E["trash"]} Список цензуры очищен.', parse_mode=ParseMode.HTML)

    else:
        await message.reply(
            f'{E["shield"]} <b>Цензура</b>\n\n'
            f'<code>!цензура добавить слово1,слово2</code> — добавить несколько слов\n'
            f'<code>!цензура удалить слово</code> — убрать слово\n'
            f'<code>!цензура список</code> — показать все запрещённые слова\n'
            f'<code>!цензура очистить</code> — удалить всё\n\n'
            f'{E["info"]} Бот молча удаляет сообщения с этими словами.',
            parse_mode=ParseMode.HTML
        )

@router.message(F.text.regexp(r'(?i)^[!]объявление'))
async def cmd_announce(message: Message):
    """Красивое объявление от имени бота."""
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_staff(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только персонал может делать объявления.</b>', parse_mode=ParseMode.HTML)
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply(f'{E["warn"]} Использование: <code>!объявление [текст]</code>', parse_mode=ParseMode.HTML)
        return
    text = parts[1]
    mod_name = message.from_user.full_name
    try:
        await message.delete()
    except:
        pass
    await message.answer(
        f'{E["mega"]} <b>Объявление</b>\n\n'
        f'{text}\n\n'
        f'<i>— {mention_html(mod_name, message.from_user.id)}</i>',
        parse_mode=ParseMode.HTML
    )

@router.message(F.text.regexp(r'(?i)^[!]предупреждения$'))
async def cmd_check_warns(message: Message):
    """Проверить варны пользователя (ответ на сообщение)."""
    if not await check_access_info(message):
        return
    db = load_db()
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    else:
        target = message.from_user
    udata = get_user(db, target.id, message.chat.id)
    warns = udata.get("warns", 0)
    violations = udata.get("violations", 0)
    emoji = E["check"] if warns == 0 else (E["warn"] if warns < 3 else E["cross"])
    await message.reply(
        f'{emoji} <b>Предупреждения {mention_html(target.full_name, target.id)}:</b> <b>{warns}/3</b>\n'
        f'<b>L</b> Всего нарушений: <b>{violations}</b>',
        parse_mode=ParseMode.HTML
    )

@router.message(F.text.regexp(r'(?i)^[!]репзнак'))
async def cmd_rep_give(message: Message):
    """Вручную изменить репутацию: !репзнак +5 или !репзнак -3 (ответ на сообщение)."""
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_staff(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только персонал.</b>', parse_mode=ParseMode.HTML)
        return
    if not message.reply_to_message:
        await message.reply(f'{E["warn"]} <b>Ответьте на сообщение пользователя.</b>', parse_mode=ParseMode.HTML)
        return
    parts = message.text.split()
    if len(parts) < 2 or not re.match(r'^[+-]\d+$', parts[1]):
        await message.reply(f'{E["warn"]} Использование: <code>!репзнак +5</code> или <code>!репзнак -3</code>', parse_mode=ParseMode.HTML)
        return
    change = int(parts[1])
    target = message.reply_to_message.from_user
    udata = get_user(db, target.id, message.chat.id)
    udata["reputation"] = udata.get("reputation", 0) + change
    save_db(db)
    change_str = f"+{change}" if change > 0 else str(change)
    await message.reply(
        f'{E["star"]} {mention_html(target.full_name, target.id)}: репутация <b>{change_str}</b> → <b>{udata["reputation"]}</b>',
        parse_mode=ParseMode.HTML
    )

# ─── Приветствие новых участников ────────────────────────────────────────────

@router.chat_member()
async def new_member_welcome(update: ChatMemberUpdated):
    global WELCOME_GIF_ID
    old = update.old_chat_member
    new = update.new_chat_member
    joined = (
        old.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED, ChatMemberStatus.RESTRICTED]
        and new.status == ChatMemberStatus.MEMBER
    )
    if not joined:
        return
    db = load_db()
    chat_id = update.chat.id
    if str(chat_id) not in db.get("groups", {}):
        return
    group = get_group(db, chat_id)
    if not group.get("settings", {}).get("welcome", True):
        return
    user = new.user
    name = mention_html(user.full_name, user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Правила чата",
            icon_custom_emoji_id="5206626000665868017",
            callback_data="show_rules_welcome"
        )]
    ])
    caption = (
        f'<blockquote>{E["party"]} {name}, добро пожаловать в чат!\n\n'
        f'{E["book"]} Прочти правила по кнопке ниже.</blockquote>'
    )
    gif_path = "emoji.mp4"
    if os.path.exists(gif_path):
        try:
            if WELCOME_GIF_ID:
                await update.bot.send_animation(
                    chat_id, WELCOME_GIF_ID,
                    caption=caption, parse_mode=ParseMode.HTML, reply_markup=kb
                )
            else:
                msg = await update.bot.send_animation(
                    chat_id, FSInputFile(gif_path),
                    caption=caption, parse_mode=ParseMode.HTML, reply_markup=kb
                )
                WELCOME_GIF_ID = msg.animation.file_id
        except Exception:
            await update.bot.send_message(chat_id, caption, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await update.bot.send_message(chat_id, caption, parse_mode=ParseMode.HTML, reply_markup=kb)

@router.callback_query(F.data == "show_rules_welcome")
async def show_rules_welcome_cb(call: CallbackQuery):
    db = load_db()
    group = get_group(db, call.message.chat.id)
    rules = group.get("rules", "Правила не установлены.")
    text = f'{E["book"]} <b>Правила чата</b>\n\n<blockquote>{rules}</blockquote>'
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Закрыть", icon_custom_emoji_id="5278578973595427038", callback_data="close_msg")]
    ])
    # Если сообщение с медиа (гиф/фото) — редактируем caption, иначе text
    if call.message.content_type in ("animation", "photo", "video", "document"):
        try:
            await call.message.edit_caption(caption=text, parse_mode=ParseMode.HTML, reply_markup=kb)
        except Exception:
            await call.answer(rules[:200], show_alert=True)
    else:
        try:
            await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        except Exception:
            await call.answer(rules[:200], show_alert=True)
    await call.answer()

# ─── Управление титулами репутации ───────────────────────────────────────────

@router.message(F.text.regexp(r'(?i)^[!]титулы$'))
async def cmd_list_titles(message: Message):
    if not await check_access_info(message):
        return
    db = load_db()
    group = get_group(db, message.chat.id)
    titles = group.get("rep_titles", [])
    if not titles:
        await message.reply(
            f'{E["info"]} <b>Титулы репутации не настроены.</b>\n\n'
            f'Добавьте: <code>!добавититул [мин] [макс] [название]</code>\n'
            f'Пример: <code>!добавититул 0 9 Новичок</code>',
            parse_mode=ParseMode.HTML
        )
        return
    lines = []
    for i, t in enumerate(sorted(titles, key=lambda x: x["min"]), 1):
        lines.append(f'<b>{i}.</b> {t["min"]}…{t["max"]} — <b>{t["title"]}</b>')
    await message.reply(
        f'{E["star"]} <b>Титулы репутации:</b>\n\n' + '\n'.join(lines) + '\n\n'
        f'{E["info"]} Удалить: <code>!удалититул [номер]</code>',
        parse_mode=ParseMode.HTML
    )

@router.message(F.text.regexp(r'(?i)^[!]добавититул'))
async def cmd_add_title(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_admin(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только администраторы.</b>', parse_mode=ParseMode.HTML)
        return
    parts = message.text.split(maxsplit=3)
    if len(parts) < 4 or not parts[1].lstrip('-').isdigit() or not parts[2].lstrip('-').isdigit():
        await message.reply(
            f'{E["warn"]} Использование: <code>!добавититул [мин] [макс] [название]</code>\n'
            f'Пример: <code>!добавититул 0 9 Новичок</code>',
            parse_mode=ParseMode.HTML
        )
        return
    mn, mx, title = int(parts[1]), int(parts[2]), parts[3]
    group = get_group(db, message.chat.id)
    titles = group.get("rep_titles", [])
    titles.append({"min": mn, "max": mx, "title": title})
    group["rep_titles"] = titles
    save_db(db)
    await message.reply(
        f'{E["check"]} Добавлен титул: <b>{title}</b> (от {mn} до {mx} реп.)',
        parse_mode=ParseMode.HTML
    )

@router.message(F.text.regexp(r'(?i)^[!]удалититул'))
async def cmd_del_title(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_admin(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только администраторы.</b>', parse_mode=ParseMode.HTML)
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.reply(f'{E["warn"]} Использование: <code>!удалититул [номер]</code>', parse_mode=ParseMode.HTML)
        return
    idx = int(parts[1]) - 1
    group = get_group(db, message.chat.id)
    titles = sorted(group.get("rep_titles", []), key=lambda x: x["min"])
    if idx < 0 or idx >= len(titles):
        await message.reply(f'{E["cross"]} Номер не найден. Список: <code>!титулы</code>', parse_mode=ParseMode.HTML)
        return
    removed = titles.pop(idx)
    group["rep_titles"] = titles
    save_db(db)
    await message.reply(
        f'{E["trash"]} Удалён титул: <b>{removed["title"]}</b>',
        parse_mode=ParseMode.HTML
    )

@router.message(F.text.regexp(r'(?i)^[!]очисттитулы$'))
async def cmd_clear_titles(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_admin(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только администраторы.</b>', parse_mode=ParseMode.HTML)
        return
    group = get_group(db, message.chat.id)
    group["rep_titles"] = []
    save_db(db)
    await message.reply(f'{E["trash"]} Все титулы репутации удалены.', parse_mode=ParseMode.HTML)

@router.message(F.chat.type.in_({"group", "supergroup"}))
async def track_messages(message: Message):
    if not message.from_user or message.from_user.is_bot:
        return

    chat_id = message.chat.id
    uid = message.from_user.id
    text_raw = (message.text or "").strip()

    # ── Staff wizard: обрабатываем ввод в чат ──────────────────────────────
    wiz = STAFF_WIZARD.get(chat_id, {}).get(uid)
    if wiz:
        step = wiz.get("step")
        msg_id = wiz.get("msg_id")

        # Шаг 1: ждём @username или ID
        if step == "awaiting_user":
            if text_raw.startswith('/'):
                STAFF_WIZARD.get(chat_id, {}).pop(uid, None)
                await message.reply(f'{E["cross"]} Отменено.', parse_mode=ParseMode.HTML)
                return
            db_w = load_db()
            target_id = None
            target_name = None
            if text_raw.startswith('@'):
                uname_q = text_raw[1:]
                for udata in db_w["users"].values():
                    if (udata.get("username") or "").lower() == uname_q.lower() and udata.get("chat_id") == chat_id:
                        target_id = udata["user_id"]
                        target_name = udata.get("first_name") or uname_q
                        break
                if target_id is None:
                    await message.reply(
                        f'{E["cross"]} <b>@{uname_q}</b> не найден.\n'
                        f'{E["info"]} Пользователь должен написать хотя бы одно сообщение в чате.',
                        parse_mode=ParseMode.HTML
                    )
                    return
            elif text_raw.lstrip('-').isdigit():
                target_id = int(text_raw)
                key2 = f"{chat_id}_{target_id}"
                if key2 in db_w["users"]:
                    target_name = db_w["users"][key2].get("first_name") or str(target_id)
                else:
                    try:
                        mbr = await message.bot.get_chat_member(chat_id, target_id)
                        target_name = mbr.user.full_name
                    except Exception:
                        await message.reply(
                            f'{E["cross"]} ID <code>{target_id}</code> не найден в чате.',
                            parse_mode=ParseMode.HTML
                        )
                        return
            else:
                await message.reply(
                    f'{E["warn"]} Укажите @username или числовой ID.',
                    parse_mode=ParseMode.HTML
                )
                return
            wiz["target_id"] = target_id
            wiz["target_name"] = target_name
            wiz["step"] = "awaiting_role"
            group_w = get_group(db_w, chat_id)
            kb_rows = []
            for rk in ROLE_KEYS:
                rname = get_role_display_name(group_w, rk)
                kb_rows.append([InlineKeyboardButton(text=rname, callback_data=f"swrole|{rk}|{target_id}")])
            kb_rows.append([InlineKeyboardButton(text="Отмена", icon_custom_emoji_id="5278578973595427038", callback_data="staff_wiz_cancel")])
            try:
                await message.bot.edit_message_text(
                    f'{E["pencil"]} <b>Добавление сотрудника</b>\n\n'
                    f'Пользователь: <b>{target_name}</b> [<code>{target_id}</code>]\n\n'
                    f'<b>Шаг 2 из 3</b> — Выберите должность:',
                    chat_id=chat_id, message_id=msg_id,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows)
                )
            except Exception:
                pass
            try:
                await message.delete()
            except Exception:
                pass
            return

        # Шаг 3а: ждём кастомное звание для нового сотрудника
        if step == "awaiting_title_new":
            if text_raw.startswith('/'):
                STAFF_WIZARD.get(chat_id, {}).pop(uid, None)
                await message.reply(f'{E["cross"]} Отменено.', parse_mode=ParseMode.HTML)
                return
            target_id = wiz["target_id"]
            target_name = wiz["target_name"]
            role_key = wiz["role_key"]
            STAFF_WIZARD.get(chat_id, {}).pop(uid, None)
            db_w = load_db()
            group_w = get_group(db_w, chat_id)
            uid_str_w = str(target_id)
            for rk in ROLE_KEYS:
                if uid_str_w in group_w["staff"].get(rk, []):
                    group_w["staff"][rk].remove(uid_str_w)
            group_w["staff"].setdefault(role_key, [])
            if uid_str_w not in group_w["staff"][role_key]:
                group_w["staff"][role_key].append(uid_str_w)
            group_w.setdefault("staff_titles", {})[uid_str_w] = text_raw
            save_db(db_w)
            role_name_w = get_role_display_name(group_w, role_key)
            try:
                await message.delete()
            except Exception:
                pass
            try:
                await message.bot.edit_message_text(
                    f'{E["check"]} <b>{target_name}</b> добавлен как <b>{role_name_w}</b> со званием «<b>{text_raw}</b>».',
                    chat_id=chat_id, message_id=msg_id,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="В список персонала", icon_custom_emoji_id="5298668674532538341", callback_data="panel_staff")]
                    ])
                )
            except Exception:
                pass
            return

        # Шаг редактирования звания существующего сотрудника
        if step == "awaiting_title_edit":
            if text_raw.startswith('/'):
                STAFF_WIZARD.get(chat_id, {}).pop(uid, None)
                await message.reply(f'{E["cross"]} Отменено.', parse_mode=ParseMode.HTML)
                return
            target_id = wiz["target_id"]
            STAFF_WIZARD.get(chat_id, {}).pop(uid, None)
            db_w = load_db()
            group_w = get_group(db_w, chat_id)
            group_w.setdefault("staff_titles", {})[str(target_id)] = text_raw
            save_db(db_w)
            try:
                await message.delete()
            except Exception:
                pass
            try:
                await message.bot.edit_message_text(
                    f'{E["check"]} Звание обновлено на «<b>{text_raw}</b>».',
                    chat_id=chat_id, message_id=msg_id,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="В список персонала", icon_custom_emoji_id="5298668674532538341", callback_data="panel_staff")]
                    ])
                )
            except Exception:
                pass
            return

    db = load_db()
    if str(chat_id) not in db.get("groups", {}):
        return
    warned = db.get("warned_owners", {})
    try:
        admins = await message.bot.get_chat_administrators(chat_id)
        for a in admins:
            if a.status == ChatMemberStatus.CREATOR:
                if str(a.user.id) in warned and warned[str(a.user.id)] >= 3:
                    return
    except:
        pass
    user = message.from_user
    uid = user.id
    group = get_group(db, chat_id)
    check_stats_date(group)
    uid_str = str(uid)
    name_now = user.full_name
    # сегодня
    if uid_str not in group["stats_today"]:
        group["stats_today"][uid_str] = {"count": 0, "name": name_now}
    group["stats_today"][uid_str]["count"] += 1
    group["stats_today"][uid_str]["name"] = name_now
    # неделя
    if "stats_week" not in group:
        group["stats_week"] = {}
    if uid_str not in group["stats_week"]:
        group["stats_week"][uid_str] = {"count": 0, "name": name_now}
    group["stats_week"][uid_str]["count"] += 1
    group["stats_week"][uid_str]["name"] = name_now
    # месяц
    if "stats_month" not in group:
        group["stats_month"] = {}
    if uid_str not in group["stats_month"]:
        group["stats_month"][uid_str] = {"count": 0, "name": name_now}
    group["stats_month"][uid_str]["count"] += 1
    group["stats_month"][uid_str]["name"] = name_now
    group["total_messages"] = group.get("total_messages", 0) + 1
    udata = get_user(db, uid, chat_id)
    udata["stats_all_count"] = udata.get("stats_all_count", 0) + 1
    udata["first_name"] = user.full_name
    udata["username"] = user.username or ""
    # Сбрасываем устаревшие ban_expires (старая логика, теперь используем muted_until)
    if udata.get("banned") and udata.get("ban_expires"):
        try:
            expires = datetime.strptime(udata["ban_expires"], "%Y-%m-%d %H:%M")
            if datetime.now() > expires:
                udata["banned"] = False
                udata["ban_expires"] = None
                udata["warns"] = 0
                save_db(db)
        except:
            pass
    if db.get("global_bans", {}).get(uid_str):
        try:
            await message.bot.ban_chat_member(chat_id, uid)
            await message.answer(
                f'{E["lock"]} {mention_html(user.full_name, uid)} заблокирован(а) (глобальный бан).',
                parse_mode=ParseMode.HTML
            )
        except:
            pass
        save_db(db)
        return
    settings = group.get("settings", {})

    # ── Мут — если пользователь замучен, удаляем сообщение и переприменяем ограничение ──
    if udata.get("muted_until"):
        try:
            muted_until_dt = datetime.strptime(udata["muted_until"], "%Y-%m-%d %H:%M")
            if datetime.now() < muted_until_dt:
                try:
                    await message.delete()
                except:
                    pass
                try:
                    await message.bot.restrict_chat_member(
                        chat_id, uid,
                        permissions=ChatPermissions(
                            can_send_messages=False,
                            can_send_audios=False,
                            can_send_documents=False,
                            can_send_photos=False,
                            can_send_videos=False,
                            can_send_video_notes=False,
                            can_send_voice_notes=False,
                            can_send_polls=False,
                            can_send_other_messages=False,
                            can_add_web_page_previews=False,
                        ),
                        until_date=muted_until_dt
                    )
                except:
                    pass
                save_db(db)
                return
            else:
                udata["muted_until"] = None
                save_db(db)
        except:
            pass

    # ── Цензура — молча удаляем сообщения с запрещёнными словами ──
    censor_words = group.get("censorship", [])
    if censor_words and (message.text or message.caption):
        msg_text_low = (message.text or message.caption or "").lower()
        for cword in censor_words:
            if cword in msg_text_low:
                try:
                    await message.delete()
                except:
                    pass
                save_db(db)
                return

    # ── Антиспам ──
    if settings.get("antispam", False) and not is_staff(db, uid, chat_id):
        is_sticker = bool(message.sticker)
        msg_text_for_spam = message.text if message.text else None
        if _check_spam(chat_id, uid, msg_text_for_spam, is_sticker):
            try:
                await message.delete()
            except:
                pass
            udata["warns"] = udata.get("warns", 0) + 1
            warns = udata["warns"]
            save_db(db)
            warn_msg = await message.answer(
                f'{E["warn"]} {mention_html(user.full_name, uid)}, антиспам! Предупреждение <b>{warns}/3</b>.',
                parse_mode=ParseMode.HTML
            )
            await asyncio.sleep(5)
            try:
                await warn_msg.delete()
            except:
                pass
            if warns >= 3:
                until = datetime.now() + timedelta(days=7)
                try:
                    await message.bot.restrict_chat_member(
                        chat_id, uid,
                        permissions=ChatPermissions(can_send_messages=False),
                        until_date=until
                    )
                except:
                    pass
            return

    if settings.get("antilinks", False) and not is_staff(db, uid, chat_id):
        text = message.text or message.caption or ""
        if re.search(r'(https?://|t\.me/|@\w+)', text):
            try:
                await message.delete()
                await message.answer(
                    f'{E["cross"]} {mention_html(user.full_name, uid)}, ссылки запрещены!',
                    parse_mode=ParseMode.HTML
                )
            except:
                pass
    if message.text:
        text_low = message.text.lower().strip()
        if message.reply_to_message and message.reply_to_message.from_user:
            replied_user = message.reply_to_message.from_user
            if replied_user.id != uid:
                rep_plus = group.get("rep_triggers_plus", [])
                rep_minus = group.get("rep_triggers_minus", [])
                daily_limit = group.get("rep_daily_limit", 5)
                today_str = str(date.today())
                given_today = udata.get("rep_given_today", {})
                if not isinstance(given_today, dict) or given_today.get("date") != today_str:
                    given_today = {"date": today_str, "count": 0, "targets": {}}
                given_count = given_today.get("count", 0)
                targets_today = given_today.get("targets", {})
                if not isinstance(targets_today, dict):
                    targets_today = {}
                rep_change = 0
                if text_low in [t.lower() for t in rep_plus]:
                    rep_change = 1
                elif text_low in [t.lower() for t in rep_minus]:
                    rep_change = -1
                if rep_change != 0:
                    if given_count >= daily_limit:
                        await message.reply(
                            f'{E["warn"]} Вы достигли дневного лимита репутации (<b>{daily_limit}</b> в день).',
                            parse_mode=ParseMode.HTML
                        )
                    else:
                        # Проверка кулдауна на конкретного пользователя
                        cooldown_h = group.get("rep_cooldown_hours", 0.0)
                        target_key = str(replied_user.id)
                        last_ts = targets_today.get(target_key, 0)
                        if cooldown_h > 0 and (time.time() - last_ts) < cooldown_h * 3600:
                            remaining = int(cooldown_h * 3600 - (time.time() - last_ts)) // 60
                            await message.reply(
                                f'{E["clock"]} Кулдаун: подождите ещё <b>{remaining} мин.</b> перед следующей оценкой этого пользователя.',
                                parse_mode=ParseMode.HTML
                            )
                        else:
                            rep_udata = get_user(db, replied_user.id, chat_id)
                            rep_udata["reputation"] = rep_udata.get("reputation", 0) + rep_change
                            new_rep = rep_udata["reputation"]
                            given_today["count"] = given_count + 1
                            given_today["date"] = today_str
                            targets_today[target_key] = time.time()
                            given_today["targets"] = targets_today
                            udata["rep_given_today"] = given_today
                            change_str = f"+{rep_change}" if rep_change > 0 else str(rep_change)
                            r_link = mention_html(replied_user.full_name, replied_user.id)
                            group2 = get_group(db, chat_id)
                            title = get_rep_title(new_rep, group2)
                            await message.reply(
                                f'{E["star"]} {r_link} получил(а) <b>{change_str}</b> к репутации!\n'
                                f'<b>L</b> Итого: <b>{new_rep}</b> — {title}',
                                parse_mode=ParseMode.HTML
                            )
    save_db(db)

@router.message(Command("clear"))
async def cmd_clear(message: Message):
    if message.from_user.id != OWNER_ID:
        await message.reply(f'{E["cross"]} <b>Только владелец бота может очищать чат.</b>', parse_mode=ParseMode.HTML)
        return
    if message.chat.type == "private":
        await message.reply(f'{E["warn"]} <b>Работает только в группах.</b>', parse_mode=ParseMode.HTML)
        return
    notice = await message.answer(f'{E["clock"]} <b>Очистка чата...</b>', parse_mode=ParseMode.HTML)
    deleted = 0
    # Удаляем от текущего message_id вниз, максимум 1000 сообщений
    start_id = message.message_id
    for msg_id in range(start_id, max(start_id - 1000, 0), -1):
        try:
            await message.bot.delete_message(message.chat.id, msg_id)
            deleted += 1
        except Exception:
            pass
    try:
        result = await message.bot.send_message(
            message.chat.id,
            f'{E["trash"]} <b>Чат очищен.</b> Удалено сообщений: <b>{deleted}</b>',
            parse_mode=ParseMode.HTML
        )
        await asyncio.sleep(5)
        await result.delete()
    except Exception:
        pass

async def send_log(text: str):
    """Отправить лог в бот-логгер владельцу."""
    global _log_bot
    if _log_bot is None:
        return
    try:
        await _log_bot.send_message(OWNER_ID, text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception:
        pass

async def log_action(bot, action: str, chat_id: int, chat_title: str, mod_id: int, mod_name: str, target_id: int, target_name: str, extra: str = ""):
    """Универсальный лог действия персонала."""
    try:
        chat = await bot.get_chat(chat_id)
        invite = f"https://t.me/{chat.username}" if chat.username else f"tg://openmessage?chat_id={str(chat_id).replace('-100', '')}"
    except Exception:
        invite = str(chat_id)
    text = (
        f'{E["bell"]} <b>Лог действия</b>\n\n'
        f'{E["home"]} Группа: <a href="{invite}">{chat_title}</a>\n'
        f'{E["shield"]} Модератор: {mention_html(mod_name, mod_id)} [<code>{mod_id}</code>]\n'
        f'{E["profile"]} Цель: {mention_html(target_name, target_id)} [<code>{target_id}</code>]\n'
        f'{E["warn"]} Действие: <b>{action}</b>'
    )
    if extra:
        text += f'\n{E["info"]} Детали: {extra}'
    await send_log(text)


# ─── Топ нарушителей ──────────────────────────────────────────────────────────

@router.message(F.text.regexp(r'(?i)^[!]топнарушителей$'))
async def cmd_top_violators(message: Message):
    if not await check_access_info(message):
        return
    db = load_db()
    chat_id = message.chat.id
    users_in_chat = [v for v in db["users"].values() if v.get("chat_id") == chat_id]
    sorted_v = sorted(users_in_chat, key=lambda x: x.get("violations", 0), reverse=True)[:10]
    if not sorted_v or sorted_v[0].get("violations", 0) == 0:
        await message.reply(f'{E["check"]} Нарушителей нет!', parse_mode=ParseMode.HTML)
        return
    lines = []
    for i, u in enumerate(sorted_v, 1):
        v = u.get("violations", 0)
        if v == 0:
            break
        w = u.get("warns", 0)
        name = u.get("first_name") or u.get("username") or f'[{u["user_id"]}]'
        lines.append(f'<b>{i}.</b> {mention_html(name, u["user_id"])} — <b>{v}</b> нарушений, варнов: <b>{w}/3</b>')
    await message.reply(
        f'{E["warn"]} <b>Топ нарушителей:</b>\n\n' + '\n'.join(lines),
        parse_mode=ParseMode.HTML
    )


# ─── Обнулить репутацию ───────────────────────────────────────────────────────

@router.message(F.text.regexp(r'(?i)^[!]обнулить'))
async def cmd_zero_rep(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_admin(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только администраторы.</b>', parse_mode=ParseMode.HTML)
        return
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    else:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply(f'{E["warn"]} Ответьте на сообщение или укажите @username.', parse_mode=ParseMode.HTML)
            return
        arg = parts[1].lstrip('@')
        target = None
        for u in db["users"].values():
            if (u.get("username") or "").lower() == arg.lower() and u.get("chat_id") == message.chat.id:
                class FU:
                    id = u["user_id"]
                    full_name = u.get("first_name") or arg
                target = FU()
                break
        if not target:
            await message.reply(f'{E["cross"]} Пользователь не найден в базе.', parse_mode=ParseMode.HTML)
            return
    udata = get_user(db, target.id, message.chat.id)
    old_rep = udata.get("reputation", 0)
    udata["reputation"] = 0
    save_db(db)
    await message.reply(
        f'{E["trash"]} Репутация {mention_html(target.full_name, target.id)} обнулена.\n'
        f'<blockquote>Было: <b>{old_rep}</b> → стало: <b>0</b></blockquote>',
        parse_mode=ParseMode.HTML
    )
    await log_action(message.bot, "Обнуление репутации", message.chat.id, message.chat.title or "",
                     message.from_user.id, message.from_user.full_name, target.id, target.full_name,
                     f"было {old_rep} → стало 0")


# ─── Удалить сообщение ────────────────────────────────────────────────────────

@router.message(F.text.regexp(r'(?i)^[!]дель$'))
async def cmd_del(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_staff(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только персонал.</b>', parse_mode=ParseMode.HTML)
        return
    if not message.reply_to_message:
        await message.reply(f'{E["warn"]} Ответьте на сообщение.', parse_mode=ParseMode.HTML)
        return
    try:
        await message.reply_to_message.delete()
    except Exception:
        pass
    try:
        await message.delete()
    except Exception:
        pass


# ─── Медиа вкл/выкл ──────────────────────────────────────────────────────────

@router.message(F.text.regexp(r'(?i)^[!]медиа (вкл|выкл)$'))
async def cmd_media_toggle(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_admin(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только администраторы.</b>', parse_mode=ParseMode.HTML)
        return
    enable = message.text.split()[-1].lower() == 'вкл'
    try:
        await message.bot.set_chat_permissions(
            message.chat.id,
            ChatPermissions(
                can_send_messages=True,
                can_send_audios=enable,
                can_send_documents=enable,
                can_send_photos=enable,
                can_send_videos=enable,
                can_send_video_notes=enable,
                can_send_voice_notes=enable,
                can_send_polls=enable,
                can_send_other_messages=enable,
            )
        )
        status = "разрешены" if enable else "запрещены"
        icon = E["check"] if enable else E["cross"]
        await message.reply(f'{icon} Медиафайлы <b>{status}</b> в группе.', parse_mode=ParseMode.HTML)
        await log_action(message.bot, f"Медиа {'вкл' if enable else 'выкл'}", message.chat.id,
                         message.chat.title or "", message.from_user.id, message.from_user.full_name,
                         message.from_user.id, message.from_user.full_name)
    except Exception as e:
        await message.reply(f'{E["cross"]} Ошибка: {e}', parse_mode=ParseMode.HTML)


# ─── Ридонли (закрыть/открыть чат) ──────────────────────────────────────────

@router.message(F.text.regexp(r'(?i)^[!]ридонли$'))
async def cmd_readonly_on(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_admin(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только администраторы.</b>', parse_mode=ParseMode.HTML)
        return
    try:
        await message.bot.set_chat_permissions(
            message.chat.id,
            ChatPermissions(can_send_messages=False)
        )
        await message.reply(f'{E["lock"]} <b>Чат закрыт.</b> Писать может только персонал.', parse_mode=ParseMode.HTML)
        await log_action(message.bot, "Ридонли ВКЛ", message.chat.id, message.chat.title or "",
                         message.from_user.id, message.from_user.full_name,
                         message.from_user.id, message.from_user.full_name)
    except Exception as e:
        await message.reply(f'{E["cross"]} Ошибка: {e}', parse_mode=ParseMode.HTML)

@router.message(F.text.regexp(r'(?i)^[!]открыть$'))
async def cmd_readonly_off(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_admin(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только администраторы.</b>', parse_mode=ParseMode.HTML)
        return
    try:
        await message.bot.set_chat_permissions(
            message.chat.id,
            ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            )
        )
        await message.reply(f'{E["unlock"]} <b>Чат открыт.</b> Все могут писать.', parse_mode=ParseMode.HTML)
        await log_action(message.bot, "Ридонли ВЫКЛ", message.chat.id, message.chat.title or "",
                         message.from_user.id, message.from_user.full_name,
                         message.from_user.id, message.from_user.full_name)
    except Exception as e:
        await message.reply(f'{E["cross"]} Ошибка: {e}', parse_mode=ParseMode.HTML)


# ─── Слоумод ─────────────────────────────────────────────────────────────────

@router.message(F.text.regexp(r'(?i)^[!]слоумод'))
async def cmd_slowmode(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_admin(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только администраторы.</b>', parse_mode=ParseMode.HTML)
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.reply(f'{E["warn"]} Использование: <code>!слоумод [секунды]</code>\nПример: <code>!слоумод 30</code>\n<code>!слоумод 0</code> — отключить', parse_mode=ParseMode.HTML)
        return
    delay = int(parts[1])
    delay = min(delay, 21600)
    try:
        await message.bot.set_chat_slow_mode_delay(message.chat.id, delay)
        if delay == 0:
            await message.reply(f'{E["check"]} <b>Слоумод отключён.</b>', parse_mode=ParseMode.HTML)
        else:
            await message.reply(f'{E["clock"]} <b>Слоумод:</b> {delay} сек. между сообщениями.', parse_mode=ParseMode.HTML)
        await log_action(message.bot, f"Слоумод {delay}с", message.chat.id, message.chat.title or "",
                         message.from_user.id, message.from_user.full_name,
                         message.from_user.id, message.from_user.full_name)
    except Exception as e:
        await message.reply(f'{E["cross"]} Ошибка: {e}', parse_mode=ParseMode.HTML)


# ─── Голосование ─────────────────────────────────────────────────────────────

@router.message(F.text.regexp(r'(?i)^[!]голос'))
async def cmd_vote(message: Message):
    if not await check_access_and_reply(message):
        return
    db = load_db()
    if not is_staff(db, message.from_user.id, message.chat.id):
        await message.reply(f'{E["cross"]} <b>Только персонал.</b>', parse_mode=ParseMode.HTML)
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply(f'{E["warn"]} Использование: <code>!голос [вопрос]</code>', parse_mode=ParseMode.HTML)
        return
    question = parts[1]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f'{E["check"]} Да (0)', callback_data='vote_yes_0'),
         InlineKeyboardButton(text=f'{E["cross"]} Нет (0)', callback_data='vote_no_0')],
        [InlineKeyboardButton(text='Завершить', icon_custom_emoji_id="5278578973595427038", callback_data='vote_end')],
    ])
    await message.answer(
        f'{E["bell"]} <b>Голосование</b>\n\n<blockquote>{question}</blockquote>',
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )
    try:
        await message.delete()
    except Exception:
        pass

VOTE_DATA: dict[str, dict] = {}

@router.callback_query(F.data.startswith('vote_yes_') | F.data.startswith('vote_no_'))
async def vote_cb(call: CallbackQuery):
    msg_key = f"{call.message.chat.id}_{call.message.message_id}"
    if msg_key not in VOTE_DATA:
        VOTE_DATA[msg_key] = {"yes": set(), "no": set()}
    uid = call.from_user.id
    if call.data.startswith('vote_yes_'):
        VOTE_DATA[msg_key]["yes"].add(uid)
        VOTE_DATA[msg_key]["no"].discard(uid)
    else:
        VOTE_DATA[msg_key]["no"].add(uid)
        VOTE_DATA[msg_key]["yes"].discard(uid)
    yes = len(VOTE_DATA[msg_key]["yes"])
    no = len(VOTE_DATA[msg_key]["no"])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f'{E["check"]} Да ({yes})', callback_data=f'vote_yes_{yes}'),
         InlineKeyboardButton(text=f'{E["cross"]} Нет ({no})', callback_data=f'vote_no_{no}')],
        [InlineKeyboardButton(text='Завершить', icon_custom_emoji_id="5278578973595427038", callback_data='vote_end')],
    ])
    try:
        await call.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass
    await call.answer()

@router.callback_query(F.data == 'vote_end')
async def vote_end_cb(call: CallbackQuery):
    db = load_db()
    if not is_staff(db, call.from_user.id, call.message.chat.id):
        await call.answer("Только персонал может завершить голосование.", show_alert=True)
        return
    msg_key = f"{call.message.chat.id}_{call.message.message_id}"
    data = VOTE_DATA.pop(msg_key, {"yes": set(), "no": set()})
    yes = len(data["yes"])
    no = len(data["no"])
    old = call.message.text or call.message.caption or ""
    await call.message.edit_text(
        f'{old}\n\n{E["chart"]} <b>Результат:</b> {E["check"]} Да — <b>{yes}</b> | {E["cross"]} Нет — <b>{no}</b>',
        parse_mode=ParseMode.HTML
    )
    await call.answer()


async def main():
    global _log_bot
    _log_bot = Bot(
        token=LOG_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    await dp.start_polling(bot, allowed_updates=["message", "callback_query", "my_chat_member", "chat_member"])

if __name__ == "__main__":
    asyncio.run(main())