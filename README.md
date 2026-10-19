# Kvitto Payments API

Простой синхронный backend для тарифов, платежей и уведомлений банка. Используются Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x и SQLite. Денежные суммы представлены целым числом копеек.

## Запуск

Все команды запускайте из каталога проекта `Kvitto-payment-TA-`, где находятся `README.md`, `app/` и `requirements.txt`. Если терминал открыт в родительском каталоге `Kvitto`, выполните:

```powershell
Set-Location .\Kvitto-payment-TA-
```

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

По умолчанию используется `kvitto.db` в текущем каталоге. Для другой базы задайте `DATABASE_URL`, например `sqlite:///./local.db`. Тарифы добавляются при старте без дубликатов.

### Docker Compose

```bash
docker compose up --build
```

API будет доступно на `http://localhost:8000`, файл SQLite сохраняется в named volume `kvitto-data`. Локальный запуск и Compose используют демонстрационный `WEBHOOK_SECRET` `kvitto-demo-webhook-secret`, поэтому для проверки `.env` настраивать не нужно. Для production задайте собственный секрет через окружение.

### Миграции

Схема БД управляется Alembic. Примените миграции командой `alembic upgrade head`. Для изменения схемы создайте ревизию командой `alembic revision --autogenerate -m "описание изменения"`, проверьте её и примените `alembic upgrade head`. URL базы задаётся через `DATABASE_URL`.

## Тесты и CI

```powershell
python -m pip install -r requirements-dev.txt
ruff check .
pytest -q
```

Тесты используют отдельную временную SQLite базу. GitHub Actions запускает Ruff и pytest при каждом push и pull request.

## API

### Тарифы

```bash
curl http://127.0.0.1:8000/tariffs
```

Тарифы `basic`, `standard`, `premium` стоят соответственно 990000, 1990000 и 2990000 копеек.

### Создать платёж

```bash
curl -i -X POST http://127.0.0.1:8000/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: order-42' \
  -d '{"tariff_id":1,"email":"customer@example.com","method":"card"}'
```

Для рассрочки передайте `"method":"installment"` и `"installment_months":3` (допустимы также 6 и 12). Промокод `KVITTO10` даёт скидку 10%, регистр не важен. Первый запрос с ключом идемпотентности возвращает 201, повторный — прежний платёж с 200.

### Получить платёж

```bash
curl http://127.0.0.1:8000/payments/1
```

Ответ содержит сумму в копейках, статус и сохранённый график рассрочки. Если платёж отсутствует, API возвращает 404.

### Фильтр списка платежей

```bash
curl 'http://127.0.0.1:8000/payments?email=customer@example.com&status=pending'
```

`email` и `status` можно использовать по отдельности или вместе.

### Webhook банка

Для проверки подписи в PowerShell используйте готовый секрет из Compose. Замените `1` на ID платежа со статусом `pending`:

```powershell
$secret = "kvitto-demo-webhook-secret"
$paymentId = 1 # замените на ID платежа со статусом pending
$body = '{"payment_id":' + $paymentId + ',"status":"succeeded"}'
$key = [Text.Encoding]::UTF8.GetBytes($secret)
$hmac = [Security.Cryptography.HMACSHA256]::new($key)
$signature = ([BitConverter]::ToString($hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($body)))).Replace('-', '').ToLowerInvariant()
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/webhooks/bank' -Method Post -ContentType 'application/json' -Headers @{ 'X-Signature' = $signature } -Body $body
```

Для своего секрета задайте `WEBHOOK_SECRET` в окружении перед запуском приложения и укажите то же значение в `$secret`. Демонстрационный ключ предназначен только для локальной проверки. При неверной подписи API возвращает 401. Допустимы переходы `pending → succeeded`, `pending → failed` и `succeeded → refunded`; запрещённый переход возвращает 409, отсутствующий платёж — 404.
