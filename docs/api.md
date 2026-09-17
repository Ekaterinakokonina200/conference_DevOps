# HTTP API

## 1. Общая информация

Conference Management System предоставляет HTTP API для управления
участниками научной конференции.

Локальный адрес приложения:

```text
http://127.0.0.1:8000
```

Интерактивная документация Swagger доступна по адресу:

```text
http://127.0.0.1:8000/docs
```

Все запросы и ответы используют формат JSON, если для конкретного
endpoint не указано иное.

## 2. Стандартные HTTP-коды

| Код | Назначение |
|---|---|
| 200 OK | Запрос успешно выполнен |
| 201 Created | Объект успешно создан |
| 204 No Content | Объект успешно удалён |
| 404 Not Found | Объект не найден |
| 409 Conflict | Нарушено бизнес-правило |
| 422 Unprocessable Entity | Ошибка проверки входных данных |
| 500 Internal Server Error | Внутренняя ошибка сервера |

## 3. Служебные endpoint

### 3.1. Web-интерфейс

```http
GET /
```

Возвращает главную HTML-страницу приложения.

Адрес:

```text
http://127.0.0.1:8000/
```

Успешный ответ:

```text
200 OK
```

### 3.2. Проверка работоспособности

```http
GET /health
```

Проверяет, что FastAPI-приложение запущено и отвечает на запросы.

Успешный ответ:

```text
200 OK
```

Пример ответа:

```json
{
  "status": "ok"
}
```

### 3.3. Swagger

```http
GET /docs
```

Открывает автоматически сформированную интерактивную документацию
FastAPI.

### 3.4. Сводный отчёт

```http
GET /reports/summary
```

Возвращает сводные показатели конференции.

Успешный ответ:

```text
200 OK
```

Пример ответа:

```json
{
  "participants": 3,
  "confirmed": 1,
  "payments_received": 1,
  "theses_submitted": 1,
  "hotel_required": 1
}
```

Поля ответа:

| Поле | Описание |
|---|---|
| participants | Общее количество участников |
| confirmed | Количество подтверждённых заявок |
| payments_received | Количество оплат со статусом paid |
| theses_submitted | Количество зарегистрированных тезисов |
| hotel_required | Количество запросов, где требуется гостиница |

`Report` отдельной таблицей базы данных не является.
Отчёт формируется динамически на основании существующих данных.

---

# 4. Participants

## 4.1. Создать участника

```http
POST /participants/
```

Создаёт нового участника конференции.

Тело запроса:

```json
{
  "full_name": "Иванов Иван Иванович",
  "email": "ivanov@example.com",
  "phone": "+79990000000",
  "organization": "Московский Политех"
}
```

Обязательные поля:

- `full_name`;
- `email`.

Необязательные поля:

- `phone`;
- `organization`.

Успешный ответ:

```text
201 Created
```

Пример ответа:

```json
{
  "id": 1,
  "full_name": "Иванов Иван Иванович",
  "email": "ivanov@example.com",
  "phone": "+79990000000",
  "organization": "Московский Политех"
}
```

Возможные ошибки:

| Код | Причина |
|---|---|
| 409 | Участник с таким email уже существует |
| 422 | Некорректный email или отсутствует обязательное поле |

Пример ошибки повторного email:

```json
{
  "detail": "Participant with this email already exists"
}
```

## 4.2. Получить список участников

```http
GET /participants/
```

Возвращает список всех участников.

Успешный ответ:

```text
200 OK
```

Пример ответа:

```json
[
  {
    "id": 1,
    "full_name": "Иванов Иван Иванович",
    "email": "ivanov@example.com",
    "phone": "+79990000000",
    "organization": "Московский Политех"
  }
]
```

Если участников нет, возвращается пустой список:

```json
[]
```

## 4.3. Получить участника по ID

```http
GET /participants/{participant_id}
```

Пример:

```http
GET /participants/1
```

Успешный ответ:

```text
200 OK
```

Ошибка, если участник не найден:

```text
404 Not Found
```

```json
{
  "detail": "Participant not found"
}
```

## 4.4. Изменить участника

```http
PUT /participants/{participant_id}
```

Можно передать только изменяемые поля.

Пример запроса:

```json
{
  "organization": "Новая организация",
  "phone": "+79991112233"
}
```

Успешный ответ:

```text
200 OK
```

Возможные ошибки:

| Код | Причина |
|---|---|
| 404 | Участник не найден |
| 409 | Новый email уже используется |
| 422 | Переданы некорректные данные |

## 4.5. Удалить участника

```http
DELETE /participants/{participant_id}
```

Успешный ответ:

```text
204 No Content
```

Тело ответа отсутствует.

Если участник не найден:

```text
404 Not Found
```

```json
{
  "detail": "Participant not found"
}
```

---

# 5. Applications

## 5.1. Создать заявку

```http
POST /applications/
```

Создаёт заявку участника.

Тело запроса:

```json
{
  "participant_id": 1
}
```

Новая заявка получает статус:

```text
pending
```

Успешный ответ:

```text
201 Created
```

Пример ответа:

```json
{
  "id": 1,
  "participant_id": 1,
  "status": "pending",
  "created_at": "2026-09-16T12:00:00"
}
```

Если Participant не найден:

```text
404 Not Found
```

```json
{
  "detail": "Participant not found"
}
```

## 5.2. Получить список заявок

```http
GET /applications/
```

Успешный ответ:

```text
200 OK
```

Пример:

```json
[
  {
    "id": 1,
    "participant_id": 1,
    "status": "pending",
    "created_at": "2026-09-16T12:00:00"
  }
]
```

## 5.3. Получить заявку по ID

```http
GET /applications/{application_id}
```

Если заявка существует:

```text
200 OK
```

Если заявка не найдена:

```text
404 Not Found
```

```json
{
  "detail": "Application not found"
}
```

## 5.4. Изменить статус заявки

```http
PUT /applications/{application_id}
```

Тело запроса:

```json
{
  "status": "confirmed"
}
```

Допустимые статусы:

- `pending`;
- `confirmed`;
- `rejected`.

Успешный ответ:

```text
200 OK
```

### Бизнес-правило оплаты

Заявку нельзя перевести в статус `confirmed`,
если у участника отсутствует Payment со статусом `paid`.

Если оплата отсутствует, сервер возвращает:

```text
409 Conflict
```

```json
{
  "detail": "Registration fee must be paid before confirmation"
}
```

После создания Payment со статусом `paid` повторный запрос
подтверждения должен вернуть:

```text
200 OK
```

## 5.5. Удалить заявку

```http
DELETE /applications/{application_id}
```

Успешный ответ:

```text
204 No Content
```

Если заявка не найдена:

```text
404 Not Found
```

---

# 6. Invitations

## 6.1. Создать приглашение

```http
POST /invitations/
```

Тело запроса:

```json
{
  "participant_id": 1
}
```

Новое приглашение получает статус:

```text
created
```

Успешный ответ:

```text
201 Created
```

Пример ответа:

```json
{
  "id": 1,
  "participant_id": 1,
  "status": "created",
  "sent_at": null
}
```

Если участник не найден:

```text
404 Not Found
```

## 6.2. Получить список приглашений

```http
GET /invitations/
```

Успешный ответ:

```text
200 OK
```

## 6.3. Получить приглашение по ID

```http
GET /invitations/{invitation_id}
```

Возможные ответы:

- `200 OK` — приглашение найдено;
- `404 Not Found` — приглашение отсутствует.

## 6.4. Изменить статус приглашения

```http
PUT /invitations/{invitation_id}
```

Тело запроса:

```json
{
  "status": "sent"
}
```

Допустимые статусы:

- `created`;
- `sent`;
- `accepted`;
- `declined`.

При переводе в статус `sent` поле `sent_at` заполняется
текущей датой и временем.

Успешный ответ:

```text
200 OK
```

Если приглашение не найдено:

```text
404 Not Found
```

## 6.5. Удалить приглашение

```http
DELETE /invitations/{invitation_id}
```

Успешный ответ:

```text
204 No Content
```

Если приглашение не найдено:

```text
404 Not Found
```

---

# 7. Payments

## 7.1. Создать оплату

```http
POST /payments/
```

Тело запроса:

```json
{
  "participant_id": 1,
  "amount": 1500,
  "status": "paid"
}
```

Поля:

| Поле | Обязательное | Описание |
|---|---|---|
| participant_id | Да | ID участника |
| amount | Да | Сумма, больше нуля |
| status | Нет | Статус, по умолчанию pending |

Допустимые статусы:

- `pending`;
- `paid`;
- `cancelled`.

Успешный ответ:

```text
201 Created
```

Пример ответа:

```json
{
  "id": 1,
  "participant_id": 1,
  "amount": 1500,
  "status": "paid",
  "payment_date": "2026-09-16T12:00:00"
}
```

Если Participant не найден:

```text
404 Not Found
```

Если `amount` равен нулю или меньше нуля:

```text
422 Unprocessable Entity
```

## 7.2. Получить список оплат

```http
GET /payments/
```

Успешный ответ:

```text
200 OK
```

## 7.3. Получить оплату по ID

```http
GET /payments/{payment_id}
```

Возможные ответы:

- `200 OK` — оплата найдена;
- `404 Not Found` — оплата не найдена.

## 7.4. Изменить статус оплаты

```http
PUT /payments/{payment_id}
```

Тело запроса:

```json
{
  "status": "paid"
}
```

Если статус меняется на `paid`, поле `payment_date`
заполняется текущей датой и временем.

Если статус меняется с `paid` на другой статус,
`payment_date` очищается.

Успешный ответ:

```text
200 OK
```

Если оплата не найдена:

```text
404 Not Found
```

## 7.5. Удалить оплату

```http
DELETE /payments/{payment_id}
```

Успешный ответ:

```text
204 No Content
```

Тело ответа отсутствует.

Если оплата не найдена:

```text
404 Not Found
```

```json
{
  "detail": "Payment not found"
}
```

---

# 8. Theses

## 8.1. Создать тезис

```http
POST /theses/
```

Тело запроса:

```json
{
  "participant_id": 1,
  "title": "Информационная безопасность автоматизированных систем",
  "file_url": "https://example.com/thesis.pdf"
}
```

Новому тезису присваивается статус:

```text
submitted
```

Успешный ответ:

```text
201 Created
```

Пример ответа:

```json
{
  "id": 1,
  "participant_id": 1,
  "title": "Информационная безопасность автоматизированных систем",
  "file_url": "https://example.com/thesis.pdf",
  "status": "submitted"
}
```

Если Participant не найден:

```text
404 Not Found
```

## 8.2. Получить список тезисов

```http
GET /theses/
```

Успешный ответ:

```text
200 OK
```

## 8.3. Получить тезис по ID

```http
GET /theses/{thesis_id}
```

Возможные ответы:

- `200 OK` — тезис найден;
- `404 Not Found` — тезис не найден.

## 8.4. Изменить статус тезиса

```http
PUT /theses/{thesis_id}
```

Тело запроса:

```json
{
  "status": "approved"
}
```

Допустимые статусы:

- `submitted`;
- `approved`;
- `rejected`.

Успешный ответ:

```text
200 OK
```

Если тезис не найден:

```text
404 Not Found
```

## 8.5. Удалить тезис

```http
DELETE /theses/{thesis_id}
```

Успешный ответ:

```text
204 No Content
```

Если тезис не найден:

```text
404 Not Found
```

---

# 9. Hotel Requests

## 9.1. Создать запрос на гостиницу

```http
POST /hotel-requests/
```

Пример, если гостиница требуется:

```json
{
  "participant_id": 1,
  "required": true,
  "check_in": "2026-10-10",
  "check_out": "2026-10-12"
}
```

Пример, если гостиница не требуется:

```json
{
  "participant_id": 1,
  "required": false,
  "check_in": null,
  "check_out": null
}
```

Успешный ответ:

```text
201 Created
```

Пример ответа:

```json
{
  "id": 1,
  "participant_id": 1,
  "required": true,
  "check_in": "2026-10-10",
  "check_out": "2026-10-12"
}
```

Ограничения:

- если `required = true`, обе даты обязательны;
- `check_out` должен быть позже `check_in`.

Возможные ошибки:

| Код | Причина |
|---|---|
| 404 | Participant не найден |
| 422 | Не указаны даты или даты указаны неправильно |

## 9.2. Получить список запросов

```http
GET /hotel-requests/
```

Успешный ответ:

```text
200 OK
```

## 9.3. Получить запрос по ID

```http
GET /hotel-requests/{request_id}
```

Возможные ответы:

- `200 OK` — запрос найден;
- `404 Not Found` — запрос не найден.

## 9.4. Изменить запрос

```http
PUT /hotel-requests/{request_id}
```

Тело запроса:

```json
{
  "required": true,
  "check_in": "2026-10-11",
  "check_out": "2026-10-13"
}
```

Успешный ответ:

```text
200 OK
```

Возможные ошибки:

- `404 Not Found` — запрос не найден;
- `422 Unprocessable Entity` — даты указаны неправильно.

## 9.5. Удалить запрос

```http
DELETE /hotel-requests/{request_id}
```

Успешный ответ:

```text
204 No Content
```

Если запрос не найден:

```text
404 Not Found
```

---

# 10. Основной сценарий проверки API

Последовательность проверки главного бизнес-правила:

1. Выполнить `POST /participants/`.
2. Сохранить ID созданного Participant.
3. Выполнить `POST /applications/`.
4. Сохранить ID созданного Application.
5. Выполнить `PUT /applications/{id}` со статусом `confirmed`.
6. Получить `409 Conflict`.
7. Выполнить `POST /payments/` со статусом `paid`.
8. Повторно выполнить подтверждение Application.
9. Получить `200 OK`.
10. Проверить, что статус Application равен `confirmed`.

## Ожидаемая ошибка до оплаты

```json
{
  "detail": "Registration fee must be paid before confirmation"
}
```

## Ожидаемый результат после оплаты

```json
{
  "id": 1,
  "participant_id": 1,
  "status": "confirmed",
  "created_at": "2026-09-16T12:00:00"
}
```

# 11. Валидация данных

FastAPI и Pydantic автоматически проверяют входные данные.

Ответ `422 Unprocessable Entity` возвращается, например, если:

- email имеет неправильный формат;
- отсутствует обязательное поле;
- сумма Payment равна нулю или меньше нуля;
- передан недопустимый статус;
- дата выезда раньше даты заезда;
- гостиница требуется, но даты не указаны.

# 12. Проверка через Swagger

Для ручной проверки API:

1. Запустить приложение.
2. Открыть `http://127.0.0.1:8000/docs`.
3. Выбрать endpoint.
4. Нажать `Try it out`.
5. Ввести данные.
6. Нажать `Execute`.
7. Проверить HTTP-код и тело ответа.
