# Kvitto Payments API

Простой синхронный backend для тарифов, платежей и уведомлений банка. Используются Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x и SQLite. Денежные суммы представлены целым числом копеек.

## Запуск

Все команды ниже запускайте из каталога проекта `Kvitto-payment-TA-` — там, где находятся `README.md`, `app/` и `requirements.txt`. Если терминал открыт в родительском каталоге `Kvitto`, сначала перейдите в проект:

```powershell
Set-Location .\Kvitto-payment-TA-
```

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

По умолчанию база `kvitto.db` создаётся в текущем каталоге. Для другой базы задайте `DATABASE_URL`, например `sqlite:///./local.db`. Три тарифа добавляются при старте; повторный старт не создаёт копии.

## Тесты

```powershell
pytest -q
```

Тесты используют отдельную временную SQLite базу.

## API

### Тарифы

```bash
curl http://127.0.0.1:8000/tariffs
```

Возвращаются `basic` — 990000 копеек, `standard` — 1990000 копеек и `premium` — 2990000 копеек.

### Создать платёж

```bash
curl -i -X POST http://127.0.0.1:8000/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: order-42' \
  -d '{"tariff_id":1,"email":"customer@example.com","method":"card"}'
```

Для рассрочки укажите `"method":"installment"` и `"installment_months":3` (допустимы также 6 и 12). Код `KVITTO10` снижает стоимость на 10%, регистр не важен. Новый запрос возвращает 201, повтор с тем же `Idempotency-Key` — исходный платёж с 200. Неизвестный промокод и некорректные поля возвращают 422.

### Получить платёж

```bash
curl http://127.0.0.1:8000/payments/1
```

Ответ включает сумму в копейках, статус и сохранённый график рассрочки. Для отсутствующего платежа возвращается 404.

### Webhook банка

```bash
curl -X POST http://127.0.0.1:8000/webhooks/bank \
  -H 'Content-Type: application/json' \
  -d '{"payment_id":1,"status":"succeeded"}'
```

Допустимы переходы `pending → succeeded`, `pending → failed` и `succeeded → refunded`. Запрещённый переход возвращает 409; отсутствующий платёж — 404.
