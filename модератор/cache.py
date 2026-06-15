"""
cache.py — Redis-кэш, счётчики лимитов и защита от спама.

Если Redis недоступен — автоматически переключается на in-memory fallback,
чтобы бот продолжал работать без Redis.

Ключи Redis:
  cooldown:pm:{uid}           — кулдаун личных сообщений
  cooldown:cb:{chat_id}:{uid} — кулдаун кнопок/команд в группах
  spam:{uid}:{date}           — счётчик действий пользователя за день
  rep:{uid}:{chat_id}:{date}  — счётчик выданных репутаций за день
"""

import asyncio
import logging
import time
from datetime import date
from typing import Optional

try:
    import redis.asyncio as aioredis
    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False

try:
    from aiolimiter import AsyncLimiter
    _LIMITER_AVAILABLE = True
except ImportError:
    _LIMITER_AVAILABLE = False

logger = logging.getLogger(__name__)

# ─── Конфигурация ─────────────────────────────────────────────────────────────

REDIS_URL: str = "redis://localhost:6379/0"

# Кулдауны
PM_COOLDOWN_SEC: float = 2.0
GROUP_CB_COOLDOWN_SEC: float = 2.0

# Лимиты спама (действий в день на пользователя)
SPAM_DAILY_LIMIT: int = 200

# Локальный rate-limiter: не более 30 запросов/сек глобально (один инстанс)
_local_limiter: Optional["AsyncLimiter"] = None

# ─── Состояние соединения ─────────────────────────────────────────────────────

_redis: Optional["aioredis.Redis"] = None
_redis_ok: bool = False

# In-memory fallback
_mem_cooldown_pm: dict[int, float] = {}
_mem_cooldown_cb: dict[str, float] = {}
_mem_spam: dict[str, int] = {}


async def init_redis(url: str = REDIS_URL) -> bool:
    """Инициализирует подключение к Redis. Возвращает True при успехе."""
    global _redis, _redis_ok
    if not _REDIS_AVAILABLE:
        logger.warning("cache: пакет redis не установлен, используется in-memory fallback")
        _redis_ok = False
        return False
    try:
        _redis = aioredis.from_url(url, decode_responses=True, socket_connect_timeout=2)
        await _redis.ping()
        _redis_ok = True
        logger.info("cache: Redis подключён (%s)", url)
        return True
    except Exception as e:
        logger.warning("cache: Redis недоступен (%s), используется in-memory fallback", e)
        _redis_ok = False
        return False


async def close_redis():
    """Закрывает соединение с Redis."""
    global _redis, _redis_ok
    if _redis:
        try:
            await _redis.aclose()
        except Exception:
            pass
    _redis = None
    _redis_ok = False


def init_local_limiter(rate: float = 30.0, period: float = 1.0):
    """Инициализирует локальный async rate-limiter (aiolimiter)."""
    global _local_limiter
    if _LIMITER_AVAILABLE:
        _local_limiter = AsyncLimiter(max_rate=rate, time_period=period)
        logger.info("cache: локальный лимитер инициализирован (%.0f req/%.0fs)", rate, period)
    else:
        logger.warning("cache: aiolimiter не установлен, локальный лимитер отключён")


async def acquire_local_limit() -> bool:
    """Захватывает слот локального лимитера. Возвращает False если лимит исчерпан."""
    if _local_limiter is None:
        return True
    try:
        await asyncio.wait_for(_local_limiter.acquire(), timeout=0.05)
        return True
    except asyncio.TimeoutError:
        return False


# ─── Кулдаун личных сообщений ─────────────────────────────────────────────────

async def check_pm_cooldown(uid: int) -> bool:
    """
    Проверяет кулдаун для личных сообщений.
    Возвращает True если действие разрешено (кулдаун не активен).
    Автоматически обновляет таймер при разрешении.
    """
    key = f"cooldown:pm:{uid}"
    if _redis_ok and _redis:
        try:
            exists = await _redis.exists(key)
            if exists:
                return False
            ttl_ms = int(PM_COOLDOWN_SEC * 1000)
            await _redis.set(key, "1", px=ttl_ms)
            return True
        except Exception as e:
            logger.debug("cache: Redis ошибка в check_pm_cooldown: %s", e)
            # fallback ниже

    # In-memory fallback
    now = time.time()
    last = _mem_cooldown_pm.get(uid, 0.0)
    if now - last < PM_COOLDOWN_SEC:
        return False
    _mem_cooldown_pm[uid] = now
    return True


async def check_group_cb_cooldown(chat_id: int, uid: int) -> bool:
    """
    Проверяет кулдаун для кнопок/команд в группах.
    Возвращает True если действие разрешено.
    """
    key = f"cooldown:cb:{chat_id}:{uid}"
    if _redis_ok and _redis:
        try:
            exists = await _redis.exists(key)
            if exists:
                return False
            ttl_ms = int(GROUP_CB_COOLDOWN_SEC * 1000)
            await _redis.set(key, "1", px=ttl_ms)
            return True
        except Exception as e:
            logger.debug("cache: Redis ошибка в check_group_cb_cooldown: %s", e)

    # In-memory fallback
    now = time.time()
    mem_key = f"{chat_id}_{uid}"
    last = _mem_cooldown_cb.get(mem_key, 0.0)
    if now - last < GROUP_CB_COOLDOWN_SEC:
        return False
    _mem_cooldown_cb[mem_key] = now
    return True


# ─── Счётчики спама (глобальные лимиты) ──────────────────────────────────────

# Lua-скрипт для атомарного INCR + проверки лимита
_LUA_INCR_CHECK = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], tonumber(ARGV[2]))
end
return current
"""

async def increment_spam_counter(uid: int, limit: int = SPAM_DAILY_LIMIT) -> tuple[int, bool]:
    """
    Увеличивает счётчик действий пользователя за сегодня.
    Возвращает (текущее_значение, превышен_ли_лимит).
    TTL ключа — до конца суток (86400 сек).
    """
    today = str(date.today())
    key = f"spam:{uid}:{today}"

    if _redis_ok and _redis:
        try:
            current = await _redis.eval(_LUA_INCR_CHECK, 1, key, "", "86400")
            current = int(current)
            return current, current > limit
        except Exception as e:
            logger.debug("cache: Redis ошибка в increment_spam_counter: %s", e)

    # In-memory fallback
    mem_key = f"{uid}:{today}"
    _mem_spam[mem_key] = _mem_spam.get(mem_key, 0) + 1
    current = _mem_spam[mem_key]
    return current, current > limit


async def get_spam_counter(uid: int) -> int:
    """Возвращает текущий счётчик действий пользователя за сегодня."""
    today = str(date.today())
    key = f"spam:{uid}:{today}"
    if _redis_ok and _redis:
        try:
            val = await _redis.get(key)
            return int(val) if val else 0
        except Exception:
            pass
    mem_key = f"{uid}:{today}"
    return _mem_spam.get(mem_key, 0)


async def reset_spam_counter(uid: int):
    """Сбрасывает счётчик спама для пользователя (например, при ручном сбросе)."""
    today = str(date.today())
    key = f"spam:{uid}:{today}"
    if _redis_ok and _redis:
        try:
            await _redis.delete(key)
        except Exception:
            pass
    mem_key = f"{uid}:{today}"
    _mem_spam.pop(mem_key, None)


# ─── Счётчики репутации (Redis-кэш) ──────────────────────────────────────────

async def get_rep_given_today(uid: int, chat_id: int) -> int:
    """Возвращает количество репутаций, выданных пользователем сегодня в чате."""
    today = str(date.today())
    key = f"rep:{uid}:{chat_id}:{today}"
    if _redis_ok and _redis:
        try:
            val = await _redis.get(key)
            return int(val) if val else 0
        except Exception:
            pass
    return 0


async def increment_rep_given(uid: int, chat_id: int) -> int:
    """Увеличивает счётчик выданных репутаций. Возвращает новое значение."""
    today = str(date.today())
    key = f"rep:{uid}:{chat_id}:{today}"
    if _redis_ok and _redis:
        try:
            current = await _redis.eval(_LUA_INCR_CHECK, 1, key, "", "86400")
            return int(current)
        except Exception:
            pass
    return 0


# ─── Кэш администраторов чата ─────────────────────────────────────────────────

async def get_admin_cache(chat_id: int) -> Optional[set]:
    """Возвращает кэшированный set admin user_id или None если кэш устарел."""
    key = f"admins:{chat_id}"
    if _redis_ok and _redis:
        try:
            members = await _redis.smembers(key)
            if members:
                return {int(m) for m in members}
            return None
        except Exception:
            pass
    return None


async def set_admin_cache(chat_id: int, admin_ids: set, ttl: int = 300):
    """Сохраняет кэш администраторов чата в Redis с TTL."""
    key = f"admins:{chat_id}"
    if _redis_ok and _redis:
        try:
            pipe = _redis.pipeline()
            pipe.delete(key)
            if admin_ids:
                pipe.sadd(key, *[str(i) for i in admin_ids])
                pipe.expire(key, ttl)
            await pipe.execute()
        except Exception as e:
            logger.debug("cache: ошибка set_admin_cache: %s", e)


async def invalidate_admin_cache(chat_id: int):
    """Инвалидирует кэш администраторов чата."""
    key = f"admins:{chat_id}"
    if _redis_ok and _redis:
        try:
            await _redis.delete(key)
        except Exception:
            pass


# ─── Периодический сброс in-memory данных ─────────────────────────────────────

async def periodic_cleanup():
    """
    Воркер: каждые 60 секунд очищает устаревшие записи in-memory fallback.
    Запускается как asyncio.create_task() в main().
    """
    while True:
        await asyncio.sleep(60)
        try:
            now = time.time()
            # Чистим устаревшие PM кулдауны
            expired_pm = [uid for uid, ts in _mem_cooldown_pm.items() if now - ts > PM_COOLDOWN_SEC * 10]
            for uid in expired_pm:
                _mem_cooldown_pm.pop(uid, None)

            # Чистим устаревшие CB кулдауны
            expired_cb = [k for k, ts in _mem_cooldown_cb.items() if now - ts > GROUP_CB_COOLDOWN_SEC * 10]
            for k in expired_cb:
                _mem_cooldown_cb.pop(k, None)

            # Чистим счётчики спама за прошлые дни
            today = str(date.today())
            expired_spam = [k for k in _mem_spam if not k.endswith(today)]
            for k in expired_spam:
                _mem_spam.pop(k, None)

            if expired_pm or expired_cb or expired_spam:
                logger.debug(
                    "cache: cleanup — pm:%d cb:%d spam:%d",
                    len(expired_pm), len(expired_cb), len(expired_spam)
                )
        except Exception as e:
            logger.error("cache: ошибка в periodic_cleanup: %s", e)
