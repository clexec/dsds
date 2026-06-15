"""
storage.py — Атомарная работа с JSON-базой данных.

Алгоритм записи:
  1. Взять распределённый Redlock (если Redis доступен)
  2. Открыть файл с эксклюзивной блокировкой fcntl (LOCK_EX)
  3. Прочитать актуальное состояние
  4. Применить изменения
  5. Записать atomically (через tmp-файл + rename)
  6. Снять fcntl-блокировку
  7. Освободить Redlock

Если Redis недоступен — используется только fcntl (для одного процесса).
Если fcntl недоступен (Windows) — используется portalocker как fallback.
"""

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Попытка импортировать Redlock ────────────────────────────────────────────

try:
    from aioredlock import Aioredlock, LockError
    _REDLOCK_AVAILABLE = True
except ImportError:
    _REDLOCK_AVAILABLE = False
    logger.warning("storage: aioredlock не установлен, распределённые локи отключены")

# ─── Попытка импортировать fcntl / portalocker ────────────────────────────────

try:
    import fcntl
    _FCNTL_AVAILABLE = True
    _PORTALOCKER_AVAILABLE = False
except ImportError:
    _FCNTL_AVAILABLE = False
    try:
        import portalocker
        _PORTALOCKER_AVAILABLE = True
    except ImportError:
        _PORTALOCKER_AVAILABLE = False
        logger.warning("storage: ни fcntl, ни portalocker не доступны — файловые блокировки отключены")

# ─── Глобальный Redlock-менеджер ──────────────────────────────────────────────

_redlock: Optional["Aioredlock"] = None
_LOCK_TTL = 10  # секунд — максимальное время удержания лока
_LOCK_RETRY = 3  # попыток захвата лока


def init_redlock(redis_urls: list[str]):
    """
    Инициализирует Aioredlock с указанными Redis-инстансами.
    Вызывать после init_redis() из cache.py.
    """
    global _redlock
    if not _REDLOCK_AVAILABLE:
        return
    try:
        _redlock = Aioredlock(
            redis_urls,
            retry_count=_LOCK_RETRY,
            retry_delay_min=0.05,
            retry_delay_max=0.2,
            lock_timeout=_LOCK_TTL,
        )
        logger.info("storage: Redlock инициализирован (%d инстанс(ов))", len(redis_urls))
    except Exception as e:
        logger.warning("storage: ошибка инициализации Redlock: %s", e)
        _redlock = None


async def close_redlock():
    """Закрывает соединения Redlock."""
    global _redlock
    if _redlock:
        try:
            await _redlock.destroy()
        except Exception:
            pass
    _redlock = None


# ─── Файловая блокировка (fcntl / portalocker) ────────────────────────────────

class _FileLock:
    """Контекстный менеджер для эксклюзивной файловой блокировки."""

    def __init__(self, filepath: str):
        self._path = filepath + ".lock"
        self._fh = None

    def __enter__(self):
        self._fh = open(self._path, "w")
        if _FCNTL_AVAILABLE:
            fcntl.flock(self._fh, fcntl.LOCK_EX)
        elif _PORTALOCKER_AVAILABLE:
            portalocker.lock(self._fh, portalocker.LOCK_EX)
        return self

    def __exit__(self, *args):
        if self._fh:
            if _FCNTL_AVAILABLE:
                fcntl.flock(self._fh, fcntl.LOCK_UN)
            elif _PORTALOCKER_AVAILABLE:
                portalocker.unlock(self._fh)
            self._fh.close()
            try:
                os.unlink(self._path)
            except OSError:
                pass


# ─── Атомарная запись файла ───────────────────────────────────────────────────

def _atomic_write(filepath: str, data: dict):
    """
    Записывает данные в файл атомарно:
    сначала во временный файл рядом, затем rename (атомарная операция на POSIX).
    """
    tmp_path = filepath + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, filepath)


# ─── Публичный API ────────────────────────────────────────────────────────────

@asynccontextmanager
async def db_write_lock(db_file: str):
    """
    Async context manager для безопасной записи в JSON-файл.

    Использование:
        async with db_write_lock(DB_FILE) as db:
            db["key"] = "value"
        # после выхода из блока данные автоматически записываются

    Порядок блокировок:
      1. Redlock (распределённый, если доступен)
      2. fcntl/portalocker (локальный процесс)
    """
    lock_key = f"db_write:{os.path.basename(db_file)}"
    redlock_ctx = None

    # 1. Взять Redlock
    if _redlock is not None:
        try:
            redlock_ctx = await _redlock.lock(lock_key)
        except Exception as e:
            logger.warning("storage: не удалось взять Redlock (%s), продолжаем без него", e)
            redlock_ctx = None

    # 2. Взять файловую блокировку и прочитать актуальные данные
    db_data = {}
    with _FileLock(db_file):
        try:
            if os.path.exists(db_file):
                with open(db_file, "r", encoding="utf-8") as f:
                    db_data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("storage: ошибка чтения %s: %s", db_file, e)
            db_data = {}

        try:
            yield db_data
        finally:
            # 3. Записать обновлённые данные атомарно
            try:
                _atomic_write(db_file, db_data)
            except Exception as e:
                logger.error("storage: ошибка записи %s: %s", db_file, e)

    # 4. Освободить Redlock
    if redlock_ctx is not None and _redlock is not None:
        try:
            await _redlock.unlock(redlock_ctx)
        except Exception as e:
            logger.debug("storage: ошибка освобождения Redlock: %s", e)


def read_db_sync(db_file: str) -> dict:
    """
    Синхронное чтение JSON-файла (без блокировок, только для чтения).
    Используется в load_db() как быстрое чтение без изменений.
    """
    if not os.path.exists(db_file):
        return {}
    try:
        with open(db_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("storage: ошибка чтения %s: %s", db_file, e)
        return {}


def write_db_sync(db_file: str, data: dict):
    """
    Синхронная запись JSON с файловой блокировкой (для обратной совместимости).
    Используется в force_save_db() и save_db().
    """
    with _FileLock(db_file):
        _atomic_write(db_file, data)
