#!/usr/bin/env python3
"""Patch remaining help_* callbacks and cmd_rules/cmd_staff to use tr()."""
import re

with open('bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# ── help_rep_cb ──────────────────────────────────────────────────────────────
old = (
    'async def help_rep_cb(call: CallbackQuery):\n'
    '    text = (\n'
    '        f\'{E["star"]} <b>Репутация</b>\\n\\n\'\n'
    '        f\'<b>Как работает:</b>\\n\'\n'
    '        f\'Ответь на сообщение одним из триггеров.\\n\\n\'\n'
    '        f\'<b>Повышение:</b> <code>+</code>, <code>++</code>, <code>+реп</code>, <code>уважение</code>, <code>красава</code>, <code>огонь</code>, <code>топ</code>, <code>молодец</code>, <code>спасибо</code>, <code>gg</code> и др.\\n\\n\'\n'
    '        f\'<b>Понижение:</b> <code>-</code>, <code>--</code>, <code>-реп</code>, <code>диз</code>, <code>бред</code>, <code>кринж</code>, <code>зашквар</code>, <code>дно</code> и др.\\n\\n\'\n'
    '        f\'<b>L</b> <code>!рейтинг</code> [@user] — репутация пользователя\\n\'\n'
    '        f\'<b>L</b> <code>!репутация</code> — топ-25 по репутации\\n\'\n'
    '        f\'<b>L</b> <code>!репзнак</code> +5/-3 — изменить вручную (персонал)\\n\'\n'
    '        f\'<b>L</b> <code>!титулы</code> — список титулов по репутации\\n\'\n'
    '        f\'<b>L</b> <code>!добавититул</code> [мин] [макс] [название]\\n\'\n'
    '        f\'<b>L</b> <code>!удалититул</code> [номер]\\n\\n\'\n'
    '        f\'{E["info"]} Лимит: 5 оценок в день (меняется в панели).\'\n'
    '    )\n'
    '    kb = InlineKeyboardMarkup(inline_keyboard=[\n'
    '        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="help_main")]\n'
    '    ])\n'
    '    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)\n'
)
new = (
    'async def help_rep_cb(call: CallbackQuery):\n'
    '    uid = call.from_user.id\n'
    '    text = (\n'
    '        f\'{E["star"]} <b>{tr("help_rep_title", uid)}</b>\\n\\n\'\n'
    '        f\'{tr("help_rep_text", uid)}\'\n'
    '    )\n'
    '    kb = InlineKeyboardMarkup(inline_keyboard=[\n'
    '        [InlineKeyboardButton(text=tr("back", uid), icon_custom_emoji_id="5206401524200145033", callback_data="help_main")]\n'
    '    ])\n'
    '    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)\n'
)
if old in content:
    content = content.replace(old, new, 1)
    print("✓ help_rep_cb patched")
else:
    print("✗ help_rep_cb NOT FOUND")

# ── help_unpunish_cb ─────────────────────────────────────────────────────────
old = (
    'async def help_unpunish_cb(call: CallbackQuery):\n'
    '    text = (\n'
    '        f\'{E["check"]} <b>Снятие наказаний</b>\\n\\n\'\n'
    '        f\'<b>L</b> <code>!разбан</code> — снять бан\\n\'\n'
    '        f\'<b>L</b> <code>!размут</code> — снять мут\\n\'\n'
    '        f\'<b>L</b> <code>!анварн</code> — снять 1 предупреждение\\n\'\n'
    '        f\'<b>L</b> <code>!разгбан</code> — снять глобальный бан (владелец)\\n\\n\'\n'
    '        f\'{E["info"]} Ответьте на сообщение пользователя.\'\n'
    '    )\n'
    '    kb = InlineKeyboardMarkup(inline_keyboard=[\n'
    '        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="help_main")]\n'
    '    ])\n'
    '    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)\n'
)
new = (
    'async def help_unpunish_cb(call: CallbackQuery):\n'
    '    uid = call.from_user.id\n'
    '    text = (\n'
    '        f\'{E["check"]} <b>{tr("help_unpunish_title", uid)}</b>\\n\\n\'\n'
    '        f\'{tr("help_unpunish_text", uid)}\'\n'
    '    )\n'
    '    kb = InlineKeyboardMarkup(inline_keyboard=[\n'
    '        [InlineKeyboardButton(text=tr("back", uid), icon_custom_emoji_id="5206401524200145033", callback_data="help_main")]\n'
    '    ])\n'
    '    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)\n'
)
if old in content:
    content = content.replace(old, new, 1)
    print("✓ help_unpunish_cb patched")
else:
    print("✗ help_unpunish_cb NOT FOUND")

# ── help_report_cb ───────────────────────────────────────────────────────────
old = (
    'async def help_report_cb(call: CallbackQuery):\n'
    '    text = (\n'
    '        f\'{E["bell"]} <b>Жалобы (Репорты)</b>\\n\\n\'\n'
    '        f\'<b>L</b> <code>!репорт</code> — ответом на нарушение\\n\'\n'
    '        f\'Бот тегнет администраторов и пришлёт кнопки быстрого реагирования.\'\n'
    '    )\n'
    '    kb = InlineKeyboardMarkup(inline_keyboard=[\n'
    '        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5206401524200145033", callback_data="help_main")]\n'
    '    ])\n'
    '    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)\n'
)
new = (
    'async def help_report_cb(call: CallbackQuery):\n'
    '    uid = call.from_user.id\n'
    '    text = (\n'
    '        f\'{E["bell"]} <b>{tr("help_report_title", uid)}</b>\\n\\n\'\n'
    '        f\'{tr("help_report_text", uid)}\'\n'
    '    )\n'
    '    kb = InlineKeyboardMarkup(inline_keyboard=[\n'
    '        [InlineKeyboardButton(text=tr("back", uid), icon_custom_emoji_id="5206401524200145033", callback_data="help_main")]\n'
    '    ])\n'
    '    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)\n'
)
if old in content:
    content = content.replace(old, new, 1)
    print("✓ help_report_cb patched")
else:
    print("✗ help_report_cb NOT FOUND")

# ── help_info_cb ─────────────────────────────────────────────────────────────
old_info_start = 'async def help_info_cb(call: CallbackQuery):\n    text = (\n        f\'{E["info"]} <b>Запросы информации</b>'
old_info_end = '    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)\n\n@router.callback_query(F.data == "help_settings")'
idx_s = content.find(old_info_start)
idx_e = content.find(old_info_end)
if idx_s != -1 and idx_e != -1:
    old_block = content[idx_s:idx_e + len('    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)\n')]
    new_block = (
        'async def help_info_cb(call: CallbackQuery):\n'
        '    uid = call.from_user.id\n'
        '    text = (\n'
        '        f\'{E["info"]} <b>{tr("help_info_title", uid)}</b>\\n\\n\'\n'
        '        f\'{tr("help_info_text", uid)}\'\n'
        '    )\n'
        '    kb = InlineKeyboardMarkup(inline_keyboard=[\n'
        '        [InlineKeyboardButton(text=tr("back", uid), icon_custom_emoji_id="5206401524200145033", callback_data="help_main")]\n'
        '    ])\n'
        '    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)\n'
    )
    content = content[:idx_s] + new_block + content[idx_s + len(old_block):]
    print("✓ help_info_cb patched")
else:
    print("✗ help_info_cb NOT FOUND", idx_s, idx_e)

# ── help_settings_cb ─────────────────────────────────────────────────────────
old_set_start = 'async def help_settings_cb(call: CallbackQuery):\n    text = (\n        f\'{E["settings"]} <b>Настройки</b>'
old_set_end = '    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)\n\n@router.callback_query(F.data == "help_rights")'
idx_s = content.find(old_set_start)
idx_e = content.find(old_set_end)
if idx_s != -1 and idx_e != -1:
    old_block = content[idx_s:idx_e + len('    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)\n')]
    new_block = (
        'async def help_settings_cb(call: CallbackQuery):\n'
        '    uid = call.from_user.id\n'
        '    text = (\n'
        '        f\'{E["settings"]} <b>{tr("help_settings_title", uid)}</b>\\n\\n\'\n'
        '        f\'{tr("help_settings_text", uid)}\'\n'
        '    )\n'
        '    kb = InlineKeyboardMarkup(inline_keyboard=[\n'
        '        [InlineKeyboardButton(text=tr("back", uid), icon_custom_emoji_id="5206401524200145033", callback_data="help_main")]\n'
        '    ])\n'
        '    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)\n'
    )
    content = content[:idx_s] + new_block + content[idx_s + len(old_block):]
    print("✓ help_settings_cb patched")
else:
    print("✗ help_settings_cb NOT FOUND", idx_s, idx_e)

# ── help_rights_cb ────────────────────────────────────────────────────────────
old_rights_start = 'async def help_rights_cb(call: CallbackQuery):\n    text = (\n        f\'{E["shield"]} <b>Права персонала</b>'
old_rights_end = '    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)\n\n@router.message(F.text.regexp'
idx_s = content.find(old_rights_start)
idx_e = content.find(old_rights_end, idx_s)
if idx_s != -1 and idx_e != -1:
    old_block = content[idx_s:idx_e + len('    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)\n')]
    new_block = (
        'async def help_rights_cb(call: CallbackQuery):\n'
        '    uid = call.from_user.id\n'
        '    text = (\n'
        '        f\'{E["shield"]} <b>{tr("help_rights_title", uid)}</b>\\n\\n\'\n'
        '        f\'{tr("help_rights_text", uid)}\'\n'
        '    )\n'
        '    kb = InlineKeyboardMarkup(inline_keyboard=[\n'
        '        [InlineKeyboardButton(text=tr("back", uid), icon_custom_emoji_id="5206401524200145033", callback_data="help_main")]\n'
        '    ])\n'
        '    await call.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)\n'
    )
    content = content[:idx_s] + new_block + content[idx_s + len(old_block):]
    print("✓ help_rights_cb patched")
else:
    print("✗ help_rights_cb NOT FOUND", idx_s, idx_e)

# ── cmd_rules ─────────────────────────────────────────────────────────────────
old_rules = (
    '    rules = group.get("rules", "Правила не установлены.")\n'
    '    await message.reply(\n'
    '        f\'{E["book"]} <b>Правила чата</b>\\n\\n\'\n'
    '        f\'<blockquote>{rules}\\n\\nНаказания:\\n• 1 нарушение — предупреждение.\\n• 2 нарушение — мут.\\n• 3 нарушение — бан.\\n\\n<i>Повторный бан после разбана — без предупреждений.</i></blockquote>\\n\\n\'\n'
    '        f\'{E["link"]} Канал: {CHANNEL}\',\n'
    '        parse_mode=ParseMode.HTML\n'
    '    )\n'
)
new_rules = (
    '    uid = message.from_user.id\n'
    '    rules = group.get("rules", tr("rules_not_set", uid))\n'
    '    await message.reply(\n'
    '        f\'{E["book"]} <b>{tr("rules_title", uid)}</b>\\n\\n\'\n'
    '        f\'<blockquote>{rules}\\n\\n{tr("rules_punishments", uid)}</blockquote>\\n\\n\'\n'
    '        f\'{E["link"]} {tr("channel_label", uid)}: {CHANNEL}\',\n'
    '        parse_mode=ParseMode.HTML\n'
    '    )\n'
)
if old_rules in content:
    content = content.replace(old_rules, new_rules, 1)
    print("✓ cmd_rules patched")
else:
    print("✗ cmd_rules NOT FOUND")

with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\nAll patches applied.")
