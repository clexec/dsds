import re
import os

PATH = "/home/ubuntu/dsds/модератор/bot.py"

with open(PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Обновляем вызовы tr() внутри хендлеров сообщений
# Ищем паттерн tr("key", uid)
def replace_tr_message(match):
    key = match.group(1)
    uid = match.group(2)
    return f'tr({key}, {uid}, message.chat.id)'

# Добавлена группа захвата для uid: (uid)
content = re.sub(r'tr\((["\'][^"\']+["\']),\s*(uid)\)', replace_tr_message, content)

# 2. Обновляем вызовы tr() в хендлерах callback_query
def replace_tr_call(match):
    key = match.group(1)
    return f'tr({key}, call.from_user.id, call.message.chat.id)'

content = re.sub(r'tr\((["\'][^"\']+["\']),\s*call\.from_user\.id\)', replace_tr_call, content)

with open(PATH, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied: tr() calls updated with chat_id context.")
