import json
import logging
import os
import yaml
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Конфигурация путей ───────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCALES_DIR = os.path.join(_BASE_DIR, "locales")
MISSING_FILE = os.path.join(_BASE_DIR, "missing.json")

SUPPORTED_LANGS = ("ru", "en")
DEFAULT_LANG = "ru"

# ─── Глобальное хранилище переводов ──────────────────────────────────────────
# _translations[lang][key] = text
_translations: dict[str, dict[str, str]] = {}
_lang_cache: dict[int, str] = {}

def init_i18n():
    """Загружает все YAML файлы из папки locales в память."""
    global _translations
    _translations = {}
    
    if not os.path.exists(LOCALES_DIR):
        logger.error(f"i18n: Директория {LOCALES_DIR} не найдена!")
        return

    for lang in SUPPORTED_LANGS:
        file_path = os.path.join(LOCALES_DIR, f"{lang}.yml")
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    # Если в файле есть корневой ключ (например 'ru:'), берем данные из него
                    if isinstance(data, dict) and lang in data:
                        _translations[lang] = data[lang]
                    elif isinstance(data, dict):
                        _translations[lang] = data
                    else:
                        _translations[lang] = {}
                logger.info(f"i18n: Загружен язык {lang} ({len(_translations[lang])} ключей)")
            except Exception as e:
                logger.error(f"i18n: Ошибка загрузки {file_path}: {e}")
                _translations[lang] = {}
        else:
            logger.warning(f"i18n: Файл {file_path} не найден")
            _translations[lang] = {}

# Вызываем инициализацию сразу при импорте модуля
init_i18n()

# ─── Работа с базой данных ────────────────────────────────────────────────────
_db_loader = None

def set_db_loader(loader):
    global _db_loader
    _db_loader = loader

def get_user_lang(user_id: int, chat_id: Optional[int] = None, db: Optional[dict] = None) -> str:
    if user_id in _lang_cache:
        return _lang_cache[user_id]

    user_lang = None
    if db is not None:
        for key, udata in db.get("users", {}).items():
            if udata.get("user_id") == user_id and udata.get("lang"):
                user_lang = udata["lang"]
                break

    if user_lang and user_lang in SUPPORTED_LANGS:
        _lang_cache[user_id] = user_lang
        return user_lang

    if chat_id and db:
        group = db.get("groups", {}).get(str(chat_id))
        if group and group.get("lang") in SUPPORTED_LANGS:
            return group["lang"]

    return DEFAULT_LANG

def set_user_lang(user_id: int, lang: str, db: dict) -> bool:
    if lang not in SUPPORTED_LANGS:
        return False
    _lang_cache[user_id] = lang
    updated = False
    for key, udata in db.get("users", {}).items():
        if udata.get("user_id") == user_id:
            udata["lang"] = lang
            updated = True
    if not updated:
        uid_key = f"pm_{user_id}"
        db.setdefault("users", {})[uid_key] = {"user_id": user_id, "lang": lang}
    return True

# ─── Основная функция перевода ────────────────────────────────────────────────

def tr(key_or_text: str, user_id: int, chat_id: Optional[int] = None, **kwargs) -> str:
    """
    Возвращает перевод строки.
    """
    db = _db_loader() if _db_loader else None
    lang = get_user_lang(user_id, chat_id, db)

    # Ищем в выбранном языке
    text = _translations.get(lang, {}).get(key_or_text)
    
    # Если не нашли — ищем в языке по умолчанию (ru)
    if text is None and lang != DEFAULT_LANG:
        text = _translations.get(DEFAULT_LANG, {}).get(key_or_text)
    
    # Если всё равно не нашли — возвращаем ключ
    if text is None:
        text = key_or_text
    
    # Подстановка переменных %{var}
    for k, v in kwargs.items():
        placeholder = f"%{{{k}}}"
        text = text.replace(placeholder, str(v))
    
    return text

# ─── Хендлеры команды /lang ───────────────────────────────────────────────────
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

lang_router = Router()

@lang_router.message(Command("lang"))
async def lang_cmd(message: Message):
    uid = message.from_user.id
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=tr("lang_btn_ru", uid), callback_data="set_lang_ru"),
            InlineKeyboardButton(text=tr("lang_btn_en", uid), callback_data="set_lang_en"),
        ]
    ])
    await message.answer(tr("lang_choose", uid), reply_markup=kb, parse_mode=ParseMode.HTML)

@lang_router.callback_query(F.data.in_({"set_lang_ru", "set_lang_en"}))
async def lang_cb_handler(call: CallbackQuery):
    uid = call.from_user.id
    new_lang = "ru" if call.data == "set_lang_ru" else "en"
    db = _db_loader() if _db_loader else {}
    from bot import OWNER_ID
    if uid != OWNER_ID:
        await call.answer("Только владелец бота может менять глобальный язык.", show_alert=True)
        return
    set_user_lang(uid, new_lang, db)
    for g_id, gdata in db.get("groups", {}).items():
        gdata["lang"] = new_lang
    if _db_loader:
        from bot import save_db
        save_db(db)
    msg_key = "lang_set_ru" if new_lang == "ru" else "lang_set_en"
    await call.answer(tr(msg_key, uid), show_alert=True)
    from bot import cmd_start
    await cmd_start(call.message)

@lang_router.callback_query(F.data.in_({"set_initial_lang_ru", "set_initial_lang_en"}))
async def set_initial_lang_cb(call: CallbackQuery):
    uid = call.from_user.id
    from bot import OWNER_ID
    if uid != OWNER_ID:
        await call.answer("Доступ запрещен.", show_alert=True)
        return
    new_lang = "ru" if call.data == "set_initial_lang_ru" else "en"
    db = _db_loader() if _db_loader else {}
    set_user_lang(uid, new_lang, db)
    for g_id, gdata in db.get("groups", {}).items():
        gdata["lang"] = new_lang
    if _db_loader:
        from bot import save_db
        save_db(db)
    await call.answer("Язык успешно установлен!", show_alert=True)
    from bot import cmd_start
    await cmd_start(call.message)

@lang_router.callback_query(F.data == "request_lang_change")
async def request_lang_change_cb(call: CallbackQuery):
    uid = call.from_user.id
    from bot import OWNER_ID, E
    if uid != OWNER_ID:
        await call.answer("Только владелец может это сделать.", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="ask_seyats_lang_ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="ask_seyats_lang_en"),
        ],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel_lang_request")]
    ])
    await call.message.edit_text(
        f'{E["earth"]} <b>Смена языка бота</b>\n\nДля смены глобального языка требуется одобрение @seyats.\nВыберите язык:',
        reply_markup=kb, parse_mode=ParseMode.HTML
    )

@lang_router.callback_query(F.data.startswith("ask_seyats_lang_"))
async def ask_seyats_lang_cb(call: CallbackQuery):
    new_lang = call.data.replace("ask_seyats_lang_", "")
    uid = call.from_user.id
    from bot import OWNER_ID, E
    if uid != OWNER_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Одобрить", callback_data=f"confirm_lang_change_{new_lang}"),
            InlineKeyboardButton(text="Отклонить", callback_data="reject_lang_change")
        ]
    ])
    try:
        await call.bot.send_message(OWNER_ID, f'{E["warn"]} <b>Запрос на смену языка</b>\n\nНа: <b>{new_lang.upper()}</b>', reply_markup=kb, parse_mode=ParseMode.HTML)
        await call.answer("Запрос отправлен администратору.", show_alert=True)
    except Exception as e:
        await call.answer(f"Ошибка: {e}", show_alert=True)
    await call.message.delete()

@lang_router.callback_query(F.data.startswith("confirm_lang_change_"))
async def confirm_lang_change_cb(call: CallbackQuery):
    uid = call.from_user.id
    from bot import OWNER_ID, save_db
    if uid != OWNER_ID: return
    new_lang = call.data.replace("confirm_lang_change_", "")
    db = _db_loader() if _db_loader else {}
    set_user_lang(uid, new_lang, db)
    for g_id, gdata in db.get("groups", {}).items():
        gdata["lang"] = new_lang
    if _db_loader: save_db(db)
    await call.message.edit_text(f"✅ Язык изменен на: <b>{new_lang.upper()}</b>", parse_mode=ParseMode.HTML)
    await call.answer("Язык изменен!", show_alert=True)
    try: await call.bot.send_message(OWNER_ID, f"✅ Запрос на {new_lang.upper()} одобрен!", parse_mode=ParseMode.HTML)
    except: pass

@lang_router.callback_query(F.data == "reject_lang_change")
async def reject_lang_change_cb(call: CallbackQuery):
    from bot import OWNER_ID
    if call.from_user.id != OWNER_ID: return
    await call.message.edit_text("❌ Запрос отклонен.")
    try: await call.bot.send_message(OWNER_ID, "❌ Запрос на смену языка отклонен.", parse_mode=ParseMode.HTML)
    except: pass

@lang_router.callback_query(F.data == "cancel_lang_request")
async def cancel_lang_request_cb(call: CallbackQuery):
    await call.message.delete()
    await call.message.answer("Отменено. Нажмите /start")
