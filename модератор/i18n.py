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
    import i18n as _i18n
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
    _i18n.set("file_format", "yml")
    _i18n.set("filename_format", "{locale}.{format}")
    _i18n.set("load_path", [LOCALES_DIR])
    _i18n.set("fallback", DEFAULT_LANG)
    _i18n.set("error_on_missing_translation", False)
    _i18n.set("error_on_missing_placeholder", False)
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

def get_user_lang(user_id: int, db: Optional[dict] = None) -> str:
    """
    Возвращает язык пользователя.
    Сначала проверяет кэш, затем db["users"].
    """
    if user_id in _lang_cache:
        return _lang_cache[user_id]

    lang = DEFAULT_LANG
    if db is not None:
        # Ищем пользователя в любом чате
        for key, udata in db.get("users", {}).items():
            if udata.get("user_id") == user_id:
                lang = udata.get("lang", DEFAULT_LANG)
                break

    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG

    _lang_cache[user_id] = lang
    return lang


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
        from i18n import set_db_loader
        set_db_loader(load_db)
    """
    global _db_loader
    _db_loader = loader


def tr(key_or_text: str, user_id: int, **kwargs) -> str:
    """
    Возвращает перевод строки для пользователя.

    Args:
        key_or_text: Ключ перевода (например "ban_done") или исходный текст
        user_id: Telegram user_id для определения языка
        **kwargs: Переменные для подстановки (например user="@username")

    Returns:
        Переведённая строка или исходный текст если ключ не найден
    """
    # Получаем язык пользователя
    db = _db_loader() if _db_loader else None
    lang = get_user_lang(user_id, db)

    if not _I18N_AVAILABLE:
        # Без python-i18n — возвращаем ключ как есть с подстановкой переменных
        result = key_or_text
        for k, v in kwargs.items():
            result = result.replace(f"%{{{k}}}", str(v))
        return result

    # Пробуем получить перевод
    try:
        full_key = f"{lang}.{key_or_text}"
        translated = _i18n.t(full_key, **kwargs)

        # python-i18n возвращает ключ если перевод не найден
        if translated == full_key or translated == key_or_text:
            # Пробуем fallback на русский
            if lang != DEFAULT_LANG:
                fallback_key = f"{DEFAULT_LANG}.{key_or_text}"
                fallback = _i18n.t(fallback_key, **kwargs)
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
    set_user_lang(uid, new_lang, db)

    # Сохраняем изменения в БД
    if _db_loader:
        from bot import save_db  # ленивый импорт для избежания цикла
        save_db(db)

    msg_key = "lang_set_ru" if new_lang == "ru" else "lang_set_en"
    await call.answer(tr(msg_key, uid), show_alert=True)
    await call.message.delete()
