# Conference Management System

Система управления участниками научной конференции.

Проект разработан в рамках лабораторной работы №1  
**«Сквозной проект и Git-процесс»**.

---

## 1. Назначение системы

Conference Management System предназначена для автоматизации основных процессов, связанных с организацией научной конференции.

Система позволяет:

- регистрировать участников;
- создавать заявки на участие;
- учитывать приглашения;
- регистрировать организационные взносы;
- учитывать тезисы участников;
- фиксировать потребность в гостинице;
- формировать сводный отчёт по конференции.

---

## 2. Категории пользователей

Основными пользователями системы являются:

- организатор конференции;
- секретарь конференции;
- оператор, работающий с данными участников.

---

## 3. Основные сценарии использования

Пользователь системы может:

1. Зарегистрировать нового участника.
2. Создать заявку участника.
3. Создать приглашение.
4. Изменить статус приглашения.
5. Зарегистрировать организационный взнос.
6. Подтвердить заявку после оплаты.
7. Добавить тезис участника.
8. Изменить статус тезиса.
9. Указать необходимость гостиницы.
10. Получить сводный отчёт по конференции.

---

## 4. Используемые технологии

Проект разработан с использованием:

- Python;
- FastAPI;
- SQLAlchemy;
- PostgreSQL;
- Alembic;
- Pydantic;
- pytest;
- Ruff;
- HTML;
- CSS;
- JavaScript;
- Git;
- GitHub.

---

## 5. Структура проекта

```text
conference_DevOps/
├── alembic/
│   ├── versions/
│   ├── env.py
│   ├── README
│   └── script.py.mako
│
├── app/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── application.py
│   │   ├── hotel_request.py
│   │   ├── invitation.py
│   │   ├── participant.py
│   │   ├── payment.py
│   │   └── thesis.py
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── applications.py
│   │   ├── hotel_requests.py
│   │   ├── invitations.py
│   │   ├── participants.py
│   │   ├── payments.py
│   │   ├── reports.py
│   │   └── theses.py
│   │
│   ├── schemas/
│   │
│   ├── services/
│   │   └── __init__.py
│   │
│   ├── static/
│   │   └── index.html
│   │
│   ├── __init__.py
│   ├── database.py
│   └── main.py
│
├── tests/
│
├── .env.example
├── .gitignore
├── alembic.ini
├── Makefile
├── README.md
└── requirements.txt
```

---

## 6. Основные сущности

### Participant

Участник конференции.

Основные поля:

- `id`;
- `full_name`;
- `email`;
- `phone`;
- `organization`;
- `created_at`.

### Application

Заявка участника на участие в конференции.

Основные поля:

- `id`;
- `participant_id`;
- `status`;
- `created_at`.

Допустимые статусы:

- `pending`;
- `confirmed`;
- `rejected`.

### Invitation

Приглашение участника.

Основные поля:

- `id`;
- `participant_id`;
- `status`;
- `sent_at`.

Допустимые статусы:

- `created`;
- `sent`;
- `accepted`;
- `declined`.

### Payment

Организационный взнос участника.

Основные поля:

- `id`;
- `participant_id`;
- `amount`;
- `status`;
- `payment_date`.

Допустимые статусы:

- `pending`;
- `paid`;
- `cancelled`.

### Thesis

Тезис участника.

Основные поля:

- `id`;
- `participant_id`;
- `title`;
- `file_url`;
- `status`.

Допустимые статусы:

- `submitted`;
- `approved`;
- `rejected`.

### HotelRequest

Информация о потребности участника в гостинице.

Основные поля:

- `id`;
- `participant_id`;
- `required`;
- `check_in`;
- `check_out`.

---

## 7. Схема данных

```text
Participant
│
├── Application
├── Invitation
├── Payment
├── Thesis
└── HotelRequest
```

Связи:

- `Participant 1:N Application`;
- `Participant 1:N Invitation`;
- `Participant 1:N Payment`;
- `Participant 1:N Thesis`;
- `Participant 1:N HotelRequest`.

Сводный отчёт `Report` не является отдельной таблицей.

Он формируется динамически на основании существующих данных.

---

## 8. Основное бизнес-правило

Заявка участника не может быть переведена в статус `confirmed`, если у участника отсутствует организационный взнос со статусом `paid`.

При попытке подтвердить заявку без оплаты сервер возвращает:

```text
409 Conflict
```

Пример ответа:

```json
{
  "detail": "Registration fee must be paid before confirmation"
}
```

---

## 9. Дополнительные ограничения

- Email участника должен быть уникальным.
- Сумма организационного взноса должна быть больше нуля.
- Если гостиница требуется, даты `check_in` и `check_out` обязательны.
- Дата `check_out` должна быть позже даты `check_in`.
- Некорректные статусы не принимаются API.
- Несуществующие объекты должны приводить к ответу `404 Not Found`.

---

## 10. Установка проекта

### 10.1. Клонирование репозитория

```bash
git clone https://github.com/Ekaterinakokonina200/conference_DevOps.git
```

Перейти в папку проекта:

```bash
cd conference_DevOps
```

### 10.2. Создание виртуального окружения

Для Windows:

```powershell
python -m venv .venv
```

Активировать виртуальное окружение:

```powershell
.venv\Scripts\Activate.ps1
```

### 10.3. Установка зависимостей

```powershell
pip install -r requirements.txt
```

---

## 11. Переменные окружения

Для работы приложения необходимо создать локальный файл `.env` на основе `.env.example`.

Пример:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/conference
APP_PORT=8000
```

Файл `.env` содержит локальные настройки и секретные данные и не должен попадать в Git.

Файл `.env.example` должен содержать только пример конфигурации без реального пароля.

---

## 12. База данных

Проект использует PostgreSQL.

Перед запуском приложения необходимо:

1. Установить PostgreSQL.
2. Создать базу данных, например:

```text
conference
```

3. Проверить значение `DATABASE_URL` в `.env`.

---

## 13. Миграции Alembic

Для применения всех миграций выполнить:

```powershell
alembic upgrade head
```

Проверить текущую миграцию:

```powershell
alembic current
```

Проверить последнюю доступную миграцию:

```powershell
alembic heads
```

`current` и `heads` должны указывать на актуальную revision.

---

## 14. Запуск приложения

Запустить FastAPI-сервер:

```powershell
python -m uvicorn app.main:app --reload
```

После запуска приложение будет доступно по адресу:

```text
http://127.0.0.1:8000/
```

---

## 15. Web-интерфейс

Главная страница приложения:

```text
http://127.0.0.1:8000/
```

Web UI позволяет:

- добавить участника;
- посмотреть список участников;
- создать заявку;
- зарегистрировать организационный взнос;
- получить сводный отчёт.

---

## 16. Swagger / API documentation

Интерактивная документация FastAPI доступна по адресу:

```text
http://127.0.0.1:8000/docs
```

Swagger позволяет:

- просматривать доступные HTTP endpoint'ы;
- отправлять запросы;
- проверять ответы API;
- тестировать обработку ошибок.

---

## 17. Проверка работоспособности

Для проверки состояния приложения используется:

```http
GET /health
```

Пример ответа:

```json
{
  "status": "ok"
}
```

URL:

```text
http://127.0.0.1:8000/health
```

---

## 18. HTTP API

### Служебные endpoint'ы

| Метод | Endpoint | Назначение |
|---|---|---|
| GET | `/` | Web-интерфейс |
| GET | `/health` | Проверка работоспособности |
| GET | `/reports/summary` | Сводный отчёт |

### Participants

| Метод | Endpoint | Назначение |
|---|---|---|
| POST | `/participants/` | Создать участника |
| GET | `/participants/` | Получить список участников |
| GET | `/participants/{id}` | Получить участника |
| PUT | `/participants/{id}` | Изменить участника |
| DELETE | `/participants/{id}` | Удалить участника |

### Applications

| Метод | Endpoint | Назначение |
|---|---|---|
| POST | `/applications/` | Создать заявку |
| GET | `/applications/` | Получить список заявок |
| GET | `/applications/{id}` | Получить заявку |
| PUT | `/applications/{id}` | Изменить статус заявки |
| DELETE | `/applications/{id}` | Удалить заявку |

### Invitations

| Метод | Endpoint | Назначение |
|---|---|---|
| POST | `/invitations/` | Создать приглашение |
| GET | `/invitations/` | Получить приглашения |
| GET | `/invitations/{id}` | Получить приглашение |
| PUT | `/invitations/{id}` | Изменить статус приглашения |
| DELETE | `/invitations/{id}` | Удалить приглашение |

### Payments

| Метод | Endpoint | Назначение |
|---|---|---|
| POST | `/payments/` | Зарегистрировать оплату |
| GET | `/payments/` | Получить список оплат |
| GET | `/payments/{id}` | Получить оплату |
| PUT | `/payments/{id}` | Изменить статус оплаты |

### Theses

| Метод | Endpoint | Назначение |
|---|---|---|
| POST | `/theses/` | Добавить тезис |
| GET | `/theses/` | Получить список тезисов |
| GET | `/theses/{id}` | Получить тезис |
| PUT | `/theses/{id}` | Изменить статус тезиса |
| DELETE | `/theses/{id}` | Удалить тезис |

### Hotel Requests

| Метод | Endpoint | Назначение |
|---|---|---|
| POST | `/hotel-requests/` | Добавить запрос на гостиницу |
| GET | `/hotel-requests/` | Получить запросы |
| GET | `/hotel-requests/{id}` | Получить запрос |
| PUT | `/hotel-requests/{id}` | Изменить запрос |
| DELETE | `/hotel-requests/{id}` | Удалить запрос |

---

## 19. Сводный отчёт

Endpoint:

```http
GET /reports/summary
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

Показатели:

- `participants` — общее количество участников;
- `confirmed` — количество подтверждённых заявок;
- `payments_received` — количество оплат со статусом `paid`;
- `theses_submitted` — количество зарегистрированных тезисов;
- `hotel_required` — количество записей, где требуется гостиница.

---

## 20. Обработка ошибок

API использует стандартные HTTP-коды.

Основные варианты:

- `200 OK` — запрос успешно выполнен;
- `201 Created` — объект успешно создан;
- `204 No Content` — объект успешно удалён;
- `404 Not Found` — объект не найден;
- `409 Conflict` — нарушено бизнес-правило;
- `422 Unprocessable Entity` — ошибка валидации данных;
- `500 Internal Server Error` — внутренняя ошибка сервера.

Примеры ситуаций:

- повторный email участника → `409 Conflict`;
- подтверждение заявки без оплаты → `409 Conflict`;
- отрицательная сумма платежа → `422 Unprocessable Entity`;
- неправильный статус → `422 Unprocessable Entity`;
- неправильные даты гостиницы → `422 Unprocessable Entity`;
- обращение к несуществующему объекту → `404 Not Found`.

---

## 21. Проверки качества

Перед созданием Pull Request необходимо выполнить:

```powershell
ruff check .
```

Ожидаемый результат:

```text
All checks passed!
```

Также необходимо выполнить:

```powershell
python -m pytest
```

Все тесты должны завершиться успешно.

---

## 22. Git workflow

Работа над изменениями выполняется по следующей схеме:

```text
GitHub Issue
↓
отдельная ветка
↓
осмысленные коммиты
↓
ruff check .
↓
python -m pytest
↓
Pull Request
↓
Review другого участника
↓
Approve
↓
Merge в main
```

---

## 23. Правила внесения изменений

1. Каждое функциональное изменение начинается с GitHub Issue.

2. Для каждой задачи создаётся отдельная ветка от актуального `main`.

3. Перед созданием ветки необходимо обновить `main`:

```powershell
git checkout main
git pull origin main
```

4. Название ветки должно отражать назначение изменения.

Примеры:

```text
feature/payments
feature/theses
feature/hotel-requests
feature/web-interface
docs/readme
```

5. Прямые коммиты в `main` запрещены.

6. Изменения должны быть разбиты на осмысленные коммиты.

7. Перед Pull Request обязательно выполняются:

```powershell
ruff check .
```

и:

```powershell
python -m pytest
```

8. Pull Request должен быть проверен другим участником команды.

9. Merge выполняется после успешного review.

---

## 24. Запрещённые действия

Запрещается:

- выполнять прямые коммиты в `main`;
- добавлять `.env` в репозиторий;
- добавлять реальные пароли;
- добавлять токены и секретные ключи;
- добавлять `.venv`;
- добавлять локальные базы данных;
- добавлять `__pycache__`;
- удалять тесты только для того, чтобы проверки прошли;
- отключать Ruff или другие проверки качества только ради успешного Pull Request;
- выполнять merge без review другого участника.

---

## 25. Порядок приёмки изменений

Изменение считается принятым после выполнения следующих шагов:

1. Создан GitHub Issue.
2. Создана отдельная ветка.
3. Выполнено изменение.
4. Созданы осмысленные коммиты.
5. Успешно выполнен `ruff check .`.
6. Успешно выполнен `python -m pytest`.
7. Создан Pull Request.
8. Выполнен review другим участником.
9. Получен `Approve`.
10. Изменение смержено в `main`.

---

## 26. Проверка секретов и локальных файлов

Файл `.env` не должен отслеживаться Git.

Проверка:

```powershell
git ls-files .env
```

Команда не должна выводить ничего.

Проверить, что `.env` находится в `.gitignore`:

```powershell
git check-ignore .env
```

Ожидаемый результат:

```text
.env
```

Также в репозитории не должны находиться:

```text
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
```

---

## 27. Основной сценарий проверки приложения

Для демонстрации работоспособности проекта можно выполнить следующую последовательность:

1. Создать `Participant`.
2. Создать `Application`.
3. Попытаться перевести заявку в `confirmed`.
4. Получить `409 Conflict`, так как оплата отсутствует.
5. Создать `Payment` со статусом `paid`.
6. Повторно перевести заявку в `confirmed`.
7. Получить `200 OK`.
8. Создать `Thesis`.
9. Создать `HotelRequest`.
10. Создать и отправить `Invitation`.
11. Получить `GET /reports/summary`.
12. Проверить `GET /health`.
13. Проверить Swagger `/docs`.
14. Проверить Web UI `/`.

---

## 28. Версия проекта

Первая стабильная версия проекта должна быть отмечена Git-тегом:

```text
v0.1.0
```

Тег создаётся после завершения всех изменений, проверок и merge в `main`.

Пример:

```powershell
git tag -a v0.1.0 -m "First working version"
git push origin v0.1.0
```

---

## 29. Команда проекта

Проект выполняется командой из трёх участников: 
- Коконина Екатерина Олеговна
- Баранова Мария Григорьевна
- Отхонова Амуланга Александровна


Основная разработка организована через:

- GitHub Issues;
- отдельные ветки;
- Pull Requests;
- review изменений;
- merge в `main`;
- версионирование с помощью Git-тегов.