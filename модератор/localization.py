"""
i18n.py — Интернационализация бота.

Функция tr(key_or_text, user_id, **kwargs):
  - Смотрит язык пользователя в db["users"][uid]["lang"] (по умолчанию "ru")
  - Возвращает перевод из locales/ru.yml или locales/en.yml
  - Если ключ не найден — возвращает исходный текст и записывает в missing.json
  - Поддерживает подстановку переменных через **kwargs (python-i18n %{var} синтаксис)

Команда /lang:
  - Хендлеры lang_cmd и lang_cb_handler подключаются в bot.py через router
"""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Попытка импортировать python-i18n ────────────────────────────────────────

try:
    import i18n
    _I18N_AVAILABLE = True
except ImportError:
    _I18N_AVAILABLE = False
    logger.warning("i18n: пакет python-i18n не установлен, переводы отключены")

# ─── Конфигурация путей ───────────────────────────────────────────────────────

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCALES_DIR = os.path.join(_BASE_DIR, "locales")
MISSING_FILE = os.path.join(_BASE_DIR, "missing.json")

SUPPORTED_LANGS = ("ru", "en")
DEFAULT_LANG = "ru"

# ─── Кэш языков пользователей (uid → lang) ────────────────────────────────────
# Заполняется при первом обращении и инвалидируется при смене языка

_lang_cache: dict[int, str] = {}

# ─── Инициализация python-i18n ────────────────────────────────────────────────

def init_i18n():
    """Настраивает python-i18n. Вызывать один раз при старте бота."""
    if not _I18N_AVAILABLE:
        return
    i18n.set("file_format", "yml")
    i18n.set("filename_format", "{locale}.{format}")
    # Явно регистрируем YAML лоадер
    from i18n.loaders import YamlLoader
    i18n.resource_loader.register_loader(YamlLoader, ["yml", "yaml"])
    
    if LOCALES_DIR not in i18n.load_path:
        i18n.load_path.append(LOCALES_DIR)
    i18n.set("fallback", DEFAULT_LANG)
    i18n.set("error_on_missing_translation", False)
    i18n.set("error_on_missing_placeholder", False)
    logger.info("i18n: инициализирован, locales_dir=%s", LOCALES_DIR)


# ─── Работа с missing.json ────────────────────────────────────────────────────

def _load_missing() -> dict:
    if os.path.exists(MISSING_FILE):
        try:
            with open(MISSING_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_missing(data: dict):
    try:
        with open(MISSING_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.error("i18n: не удалось записать missing.json: %s", e)


def _record_missing(key: str, lang: str):
    """Записывает отсутствующий ключ в missing.json."""
    try:
        data = _load_missing()
        if key not in data:
            data[key] = {"langs": [lang], "count": 1}
        else:
            if lang not in data[key].get("langs", []):
                data[key].setdefault("langs", []).append(lang)
            data[key]["count"] = data[key].get("count", 0) + 1
        _save_missing(data)
    except Exception as e:
        logger.debug("i18n: ошибка записи missing: %s", e)


# ─── Получение языка пользователя ────────────────────────────────────────────

def get_user_lang(user_id: int, chat_id: Optional[int] = None, db: Optional[dict] = None) -> str:
    """
    Возвращает язык для сообщения.
    Приоритет:
    1. Личный язык пользователя (если установлен)
    2. Язык группы (если chat_id указан и это группа)
    3. Язык по умолчанию (ru)
    """
    # 1. Личный язык (из кэша или БД)
    if user_id in _lang_cache:
        return _lang_cache[user_id]

    user_lang = None
    if db is not None:
        # Ищем пользователя в users. Для простоты берем первую попавшуюся запись с установленным языком
        for key, udata in db.get("users", {}).items():
            if udata.get("user_id") == user_id and udata.get("lang"):
                user_lang = udata["lang"]
                break

    if user_lang and user_lang in SUPPORTED_LANGS:
        _lang_cache[user_id] = user_lang
        return user_lang

    # 2. Язык группы
    if chat_id and db:
        group = db.get("groups", {}).get(str(chat_id))
        if group and group.get("lang") in SUPPORTED_LANGS:
            return group["lang"]

    return DEFAULT_LANG


def set_user_lang(user_id: int, lang: str, db: dict) -> bool:
    """
    Устанавливает язык пользователя в db и обновляет кэш.
    Возвращает True если язык поддерживается.
    """
    if lang not in SUPPORTED_LANGS:
        return False

    _lang_cache[user_id] = lang

    # Обновляем во всех записях пользователя (он может быть в нескольких чатах)
    updated = False
    for key, udata in db.get("users", {}).items():
        if udata.get("user_id") == user_id:
            udata["lang"] = lang
            updated = True

    # Если пользователя нет в users (например, в ЛС) — создаём запись
    if not updated:
        uid_key = f"pm_{user_id}"
        if uid_key not in db.get("users", {}):
            db.setdefault("users", {})[uid_key] = {
                "user_id": user_id,
                "lang": lang
            }
        else:
            db["users"][uid_key]["lang"] = lang

    return True


def invalidate_lang_cache(user_id: int):
    """Инвалидирует кэш языка для пользователя."""
    _lang_cache.pop(user_id, None)


# ─── Основная функция перевода ────────────────────────────────────────────────

# Ленивый импорт db для избежания циклических зависимостей
_db_loader = None

def set_db_loader(loader):
    """
    Устанавливает функцию загрузки БД (load_db из bot.py).
    Вызывать после инициализации бота:
        from localization import set_db_loader
        set_db_loader(load_db)
    """
    global _db_loader
    _db_loader = loader


def tr(key_or_text: str, user_id: int, chat_id: Optional[int] = None, **kwargs) -> str:
    """
    Возвращает перевод строки.

    Args:
        key_or_text: Ключ перевода (например "ban_done") или исходный текст
        user_id: Telegram user_id
        chat_id: ID чата (для определения языка группы)
        **kwargs: Переменные для подстановки

    Returns:
        Переведённая строка или исходный текст если ключ не найден
    """
    # Получаем язык
    db = _db_loader() if _db_loader else None
    lang = get_user_lang(user_id, chat_id, db)

    if not _I18N_AVAILABLE:
        # Без python-i18n — возвращаем ключ как есть с подстановкой переменных
        result = key_or_text
        for k, v in kwargs.items():
            result = result.replace(f"%{{{k}}}", str(v))
        return result

    # Пробуем получить перевод
    try:
        full_key = f"{lang}.{key_or_text}"
        translated = i18n.t(full_key, **kwargs)

        # python-i18n возвращает ключ если перевод не найден
        if translated == full_key or translated == key_or_text:
            # Пробуем fallback на русский
            if lang != DEFAULT_LANG:
                fallback_key = f"{DEFAULT_LANG}.{key_or_text}"
                fallback = i18n.t(fallback_key, **kwargs)
                if fallback != fallback_key and fallback != key_or_text:
                    _record_missing(key_or_text, lang)
                    return fallback

            # Ключ не найден ни в одном языке
            _record_missing(key_or_text, lang)
            # Возвращаем исходный текст с подстановкой переменных
            result = key_or_text
            for k, v in kwargs.items():
                result = result.replace(f"%{{{k}}}", str(v))
            return result

        return translated

    except Exception as e:
        logger.debug("i18n: ошибка перевода ключа '%s': %s", key_or_text, e)
        _record_missing(key_or_text, lang)
        result = key_or_text
        for k, v in kwargs.items():
            result = result.replace(f"%{{{k}}}", str(v))
        return result


# ─── Хендлеры команды /lang ───────────────────────────────────────────────────
# Импортируются и регистрируются в bot.py

from aiogram import Router as _Router, F as _F
from aiogram.filters import Command as _Command
from aiogram.types import (
    Message as _Message,
    CallbackQuery as _CallbackQuery,
    InlineKeyboardMarkup as _InlineKeyboardMarkup,
    InlineKeyboardButton as _InlineKeyboardButton,
)
from aiogram.enums import ParseMode as _ParseMode

lang_router = _Router()


@lang_router.message(_Command("lang"))
async def lang_cmd(message: _Message):
    """Команда /lang — показывает кнопки выбора языка."""
    uid = message.from_user.id
    kb = _InlineKeyboardMarkup(inline_keyboard=[
        [
            _InlineKeyboardButton(text=tr("lang_btn_ru", uid), callback_data="set_lang_ru"),
            _InlineKeyboardButton(text=tr("lang_btn_en", uid), callback_data="set_lang_en"),
        ]
    ])
    await message.answer(
        tr("lang_choose", uid),
        reply_markup=kb,
        parse_mode=_ParseMode.HTML
    )


@lang_router.callback_query(_F.data.in_({"set_lang_ru", "set_lang_en"}))
async def lang_cb_handler(call: _CallbackQuery):
    """Обрабатывает выбор языка."""
    uid = call.from_user.id
    new_lang = "ru" if call.data == "set_lang_ru" else "en"

    db = _db_loader() if _db_loader else {}
    
    # Смена языка разрешена только владельцу бота
    from bot import OWNER_ID
    if uid != OWNER_ID:
        await call.answer("Только владелец бота может менять глобальный язык.", show_alert=True)
        return

    set_user_lang(uid, new_lang, db)
    
    # Устанавливаем язык для всех существующих групп
    for g_id, gdata in db.get("groups", {}).items():
        gdata["lang"] = new_lang

    # Сохраняем изменения в БД
    if _db_loader:
        from bot import save_db
        save_db(db)

    msg_key = "lang_set_ru" if new_lang == "ru" else "lang_set_en"
    await call.answer(tr(msg_key, uid), show_alert=True)
    
    # Вместо удаления сообщения и просьбы нажать /start, вызываем /start программно
    from bot import cmd_start
    await cmd_start(call.message)

@lang_router.callback_query(_F.data.in_({"set_initial_lang_ru", "set_initial_lang_en"}))
async def set_initial_lang_cb(call: _CallbackQuery):
    """Первоначальный выбор языка владельцем."""
    uid = call.from_user.id
    from bot import OWNER_ID
    if uid != OWNER_ID:
        await call.answer("Доступ запрещен.", show_alert=True)
        return

    new_lang = "ru" if call.data == "set_initial_lang_ru" else "en"
    db = _db_loader() if _db_loader else {}
    
    set_user_lang(uid, new_lang, db)
    
    # Также ставим этот язык глобальным для всех групп
    for g_id, gdata in db.get("groups", {}).items():
        gdata["lang"] = new_lang

    if _db_loader:
        from bot import save_db
        save_db(db)

    await call.answer("Язык успешно установлен!", show_alert=True)
    from bot import cmd_start
    await cmd_start(call.message)

@lang_router.callback_query(_F.data == "request_lang_change")
async def request_lang_change_cb(call: _CallbackQuery):
    """Запрос на смену языка через одобрение @seyats."""
    uid = call.from_user.id
    from bot import OWNER_ID, E
    if uid != OWNER_ID:
        await call.answer("Только владелец может это сделать.", show_alert=True)
        return

    kb = _InlineKeyboardMarkup(inline_keyboard=[
        [
            _InlineKeyboardButton(text="🇷🇺 Русский", callback_data="ask_seyats_lang_ru"),
            _InlineKeyboardButton(text="🇬🇧 English", callback_data="ask_seyats_lang_en"),
        ],
        [_InlineKeyboardButton(text="Отмена", callback_data="cancel_lang_request")]
    ])
    
    await call.message.edit_text(
        f'{E["earth"]} <b>Смена языка бота</b>\n\n'
        f'Для смены глобального языка требуется одобрение @seyats.\n'
        f'Выберите язык, на который хотите переключиться:',
        reply_markup=kb,
        parse_mode=_ParseMode.HTML
    )

@lang_router.callback_query(_F.data.startswith("ask_seyats_lang_"))
async def ask_seyats_lang_cb(call: _CallbackQuery):
    """Отправка запроса на смену языка @seyats."""
    new_lang = call.data.replace("ask_seyats_lang_", "")
    uid = call.from_user.id
    from bot import OWNER_ID, E
    
    if uid != OWNER_ID:
        return

    # Отправляем реальный запрос администратору (владельцу)
    # Здесь OWNER_ID — это тот, кто получает уведомления.
    # Если @seyats — это OWNER_ID, то он получит сообщение.
    
    kb = _InlineKeyboardMarkup(inline_keyboard=[
        [
            _InlineKeyboardButton(text="Одобрить", callback_data=f"confirm_lang_change_{new_lang}"),
            _InlineKeyboardButton(text="Отклонить", callback_data="reject_lang_change")
        ]
    ])

    try:
        await call.bot.send_message(
            OWNER_ID,
            f'{E["warn"]} <b>Запрос на смену языка бота</b>\n\n'
            f'Владелец бота запрашивает смену глобального языка на: <b>{new_lang.upper()}</b>\n'
            f'ID владельца: <code>{uid}</code>',
            reply_markup=kb,
            parse_mode=_ParseMode.HTML
        )
        await call.answer("Запрос отправлен администратору. Ожидайте одобрения.", show_alert=True)
    except Exception as e:
        await call.answer(f"Ошибка при отправке запроса: {e}", show_alert=True)
    
    await call.message.delete()

@lang_router.callback_query(_F.data.startswith("confirm_lang_change_"))
async def confirm_lang_change_cb(call: _CallbackQuery):
    """Одобрение смены языка администратором."""
    uid = call.from_user.id
    from bot import OWNER_ID, save_db
    if uid != OWNER_ID:
        await call.answer("Доступ запрещен.", show_alert=True)
        return

    new_lang = call.data.replace("confirm_lang_change_", "")
    db = _db_loader() if _db_loader else {}
    
    # Устанавливаем язык владельцу и всем группам
    set_user_lang(uid, new_lang, db)
    for g_id, gdata in db.get("groups", {}).items():
        gdata["lang"] = new_lang

    if _db_loader:
        save_db(db)

    await call.message.edit_text(f"✅ Глобальный язык бота изменен на: <b>{new_lang.upper()}</b>", parse_mode=_ParseMode.HTML)
    await call.answer("Язык изменен!", show_alert=True)
    
    # Уведомляем владельца о смене (если это был запрос)
    try:
        await call.bot.send_message(OWNER_ID, f"✅ Ваш запрос на смену языка на <b>{new_lang.upper()}</b> одобрен!", parse_mode=_ParseMode.HTML)
    except:
        pass

@lang_router.callback_query(_F.data == "reject_lang_change")
async def reject_lang_change_cb(call: _CallbackQuery):
    """Отклонение смены языка администратором."""
    uid = call.from_user.id
    from bot import OWNER_ID
    if uid != OWNER_ID:
        await call.answer("Доступ запрещен.", show_alert=True)
        return

    await call.message.edit_text("❌ Запрос на смену языка отклонен.")
    await call.answer("Отклонено.")
    
    try:
        await call.bot.send_message(OWNER_ID, "❌ Ваш запрос на смену языка был отклонен администратором.", parse_mode=_ParseMode.HTML)
    except:
        pass

@lang_router.callback_query(_F.data == "cancel_lang_request")
async def cancel_lang_request_cb(call: _CallbackQuery):
    await call.message.delete()
    await call.message.answer("Действие отменено. Нажмите /start для возврата.")
