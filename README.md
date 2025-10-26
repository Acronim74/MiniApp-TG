```markdown
# AgentBot Minimal Secure Template — Render deployment

Коротко: проект готов к размещению на Render (managed hosting). Ниже — быстрый сценарий деплоя и настройка webhook.

1) Подготовка
- Убедись, что проект закоммичен в GitHub (ветка main).
- В корне проекта должны быть: app/, webapp/, requirements.txt, .env.example, render.yaml (опционально).

2) Деплой на Render (через веб-интерфейс)
- Зайди на https://dashboard.render.com → New → Web Service.
- Connect your GitHub repo → выбери ваш репозиторий и ветку main.
- В поле Environment выбери "Python 3".
- Build Command: оставь пустым или используй: `pip install -r requirements.txt`
- Start Command: `gunicorn -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:$PORT`
- Создавай сервис. Дождись успешного deploy — у тебя появится публичный HTTPS URL вида https://<your-service>.onrender.com.

3) Настройка переменных окружения (в Render Dashboard -> Environment)
- BOT_TOKEN = <токен твоего бота>
- WEBAPP_BASE_URL = https://<your-service>.onrender.com/webapp
- USE_JWT = true|false
- JWT_SECRET = <сильная секретная строка>  (только если USE_JWT=true)

4) Обнови .env локально (по желанию)
- Для локальной разработки оставь .env как есть, но не коммить .env в репозиторий.

5) Установка webhook Telegram (после deploy)
- Выполни (PowerShell):
  $bot = "<YOUR_BOT_TOKEN>"
  $url = "https://<your-service>.onrender.com"
  Invoke-RestMethod -Uri "https://api.telegram.org/bot$bot/setWebhook" -Method POST -Body (@{url="$url/webhook"} | ConvertTo-Json) -ContentType "application/json"
- Проверь getWebhookInfo:
  Invoke-RestMethod -Uri "https://api.telegram.org/bot$bot/getWebhookInfo" | ConvertTo-Json -Depth 4

6) Тест
- Открой бота в Telegram, отправь /start → нажми «Open WebApp» → WebApp должен отправить initData на /auth/init и показать верифицированные данные.

7) Что дальше
- Добавлять базу данных, админ интерфейс, дополнительные страницы webapp, защищённые endpoints (/me и т.д.).
```