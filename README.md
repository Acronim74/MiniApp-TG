```markdown
# AgentBot Minimal Secure Template

Цель
- Минимальный шаблон: Telegram webhook → WebApp.
- WebApp использует Telegram WebApp initData и отправляет initData на backend.
- Backend валидирует initData (с использованием BOT_TOKEN) и опционально возвращает JWT.
- Шаблон ориентирован на безопасность по умолчанию, при этом можно временно отключать выдачу JWT (USE_JWT).

Структура
- app/
  - main.py
  - config.py
  - routers/
    - webhook.py
    - auth.py
  - utils/
    - telegram_auth.py
- webapp/
  - index.html
  - static/js/app.js
- .env.example
- requirements.txt
- README.md

Быстрый старт (Windows / PowerShell)
1. Скопируйте `.env.example` в `.env` и заполните:
   - BOT_TOKEN — токен вашего Telegram‑бота.
   - WEBAPP_BASE_URL — base URL вашего webapp (например https://abcd1234.ngrok.io/webapp)
   - USE_JWT — true|false (если true, backend вернёт JWT при /auth/init; если false, backend вернёт user info, но не токен)

2. Создайте и активируйте виртуальное окружение:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Установите зависимости:
```powershell
pip install -r requirements.txt
```

4. Запустите сервер:
```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

5. Тест локально:
- Откройте http://127.0.0.1:8000/health — должен вернуть {"status":"ok"}
- Откройте webapp локально: http://127.0.0.1:8000/webapp

6. Тест webhook (через ngrok):
- ngrok http 8000
- установите webhook:
  https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://abcd1234.ngrok.io/webhook
- Напишите боту /start — бот отправит сообщение с кнопкой "Open WebApp".
- Откройте WebApp в Telegram — клиент отправит initData на backend /auth/init, backend валидирует и вернёт user info (и token если USE_JWT=true).

Безопасность
- initData проверяется сервером по алгоритму Telegram (HMAC-SHA256 с secret = SHA256(bot_token)).
- По умолчанию шаблон использует проверку initData и не даёт токены, если USE_JWT=false.
- В продакшне храните BOT_TOKEN и JWT_SECRET только в защищённых переменных окружения, не коммитьте .env.

Дальше
- Добавить БД (sqlite/postgres) и миграции (alembic).
- Добавить users/agents model и endpoint для администрирования.
- Добавить JWT flow и защиту endpoints (если USE_JWT включён).
- Добавить upload/attachments и background-обработку.

```