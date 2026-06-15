#!/usr/bin/env python3
"""
extract_strings.py — Сбор русскоязычных строк из bot.py для последующей локализации.

Запуск:
    python3 extract_strings.py

Результат:
    strings_to_localize.txt — все найденные строки с номерами строк в формате:
        LINE <номер>: <строка>
"""

import re
import sys
import os

SOURCE_FILE = os.path.join(os.path.dirname(__file__), "bot.py")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "strings_to_localize.txt")

# Регулярка для определения наличия кириллицы в строке
_CYRILLIC = re.compile(r'[а-яёА-ЯЁ]')

# Регулярки для извлечения строк из Python-кода
_STRING_PATTERNS = [
    # f"..." или f'...'
    re.compile(r'f["\']([^"\'\\]*(?:\\.[^"\'\\]*)*)["\']', re.DOTALL),
    # "..." или '...' (обычные строки)
    re.compile(r'(?<![fFrRbBuU])["\']([^"\'\\]*(?:\\.[^"\'\\]*)*)["\']', re.DOTALL),
    # Тройные кавычки
    re.compile(r'"""(.*?)"""', re.DOTALL),
    re.compile(r"'''(.*?)'''", re.DOTALL),
]

# Паттерны для извлечения текстовых аргументов из конкретных вызовов
_CALL_PATTERNS = [
    # text="...", text='...'
    re.compile(r'text\s*=\s*["\']([^"\']+)["\']'),
    # InlineKeyboardButton(text="...", ...)
    re.compile(r'InlineKeyboardButton\s*\(\s*text\s*=\s*["\']([^"\']+)["\']'),
    # .answer("..."), .reply("..."), .send_message(..., "...")
    re.compile(r'(?:answer|reply|send_message|edit_text|answer_text)\s*\(\s*["\']([^"\']+)["\']'),
    # f'...' и f"..." — извлекаем текстовые части (без {})
    re.compile(r'f["\']([^"\'{}]+(?:\{[^}]*\}[^"\'{}]*)*)["\']'),
]


def extract_russian_strings(filepath: str) -> list[tuple[int, str]]:
    """
    Извлекает все строки с кириллицей из Python-файла.
    Возвращает список (номер_строки, строка).
    """
    results = []
    seen = set()

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Пропускаем комментарии
        if stripped.startswith("#"):
            continue

        # Ищем строки с кириллицей через все паттерны
        for pattern in _CALL_PATTERNS:
            for match in pattern.finditer(line):
                text = match.group(1).strip()
                # Убираем HTML-теги для чистоты
                text_clean = re.sub(r'<[^>]+>', '', text).strip()
                # Убираем f-строковые выражения
                text_clean = re.sub(r'\{[^}]*\}', '{...}', text_clean).strip()

                if _CYRILLIC.search(text_clean) and text_clean not in seen and len(text_clean) > 2:
                    seen.add(text_clean)
                    results.append((lineno, text_clean))

        # Дополнительно ищем все строки в кавычках с кириллицей
        for pattern in _STRING_PATTERNS:
            for match in pattern.finditer(line):
                text = match.group(1).strip()
                text_clean = re.sub(r'<[^>]+>', '', text).strip()
                text_clean = re.sub(r'\{[^}]*\}', '{...}', text_clean).strip()
                text_clean = re.sub(r'\\n', ' ', text_clean).strip()

                if _CYRILLIC.search(text_clean) and text_clean not in seen and len(text_clean) > 3:
                    seen.add(text_clean)
                    results.append((lineno, text_clean))

    return sorted(results, key=lambda x: x[0])


def main():
    if not os.path.exists(SOURCE_FILE):
        print(f"Ошибка: файл {SOURCE_FILE} не найден")
        sys.exit(1)

    print(f"Сканирую {SOURCE_FILE}...")
    strings = extract_russian_strings(SOURCE_FILE)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"# Русские строки из {os.path.basename(SOURCE_FILE)}\n")
        f.write(f"# Всего найдено: {len(strings)}\n")
        f.write("# Формат: LINE <номер>: <текст>\n")
        f.write("# После получения ключей — положить в locales/ru.yml и locales/en.yml\n\n")

        current_section = 0
        for lineno, text in strings:
            section = lineno // 100
            if section != current_section:
                current_section = section
                f.write(f"\n# ── Строки {section * 100}–{(section + 1) * 100 - 1} ──\n")
            f.write(f"LINE {lineno:4d}: {text}\n")

    print(f"Готово! Найдено {len(strings)} строк.")
    print(f"Результат сохранён в: {OUTPUT_FILE}")

    # Выводим первые 20 для предпросмотра
    print("\nПервые 20 строк:")
    for lineno, text in strings[:20]:
        preview = text[:80] + "..." if len(text) > 80 else text
        print(f"  LINE {lineno:4d}: {preview}")


if __name__ == "__main__":
    main()
