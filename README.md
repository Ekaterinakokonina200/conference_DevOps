# Conference Management System

Система управления участниками научной конференции.

Проект разработан в рамках лабораторной работы №1 «Сквозной проект и Git-процесс».

## Возможности

Система позволяет:

* регистрировать участников;
* создавать заявки на участие;
* создавать приглашения;
* регистрировать организационные взносы;
* подтверждать заявки после оплаты;
* учитывать тезисы;
* учитывать потребность в гостинице;
* формировать сводный отчёт;
* работать через HTTP API;
* выполнять основные операции через Web-интерфейс;
* регистрировать учётные записи;
* выполнять вход с получением JWT;
* получать текущего пользователя;
* выходить через Web-интерфейс.

## Основное бизнес-правило

Application нельзя перевести в статус `confirmed`, если у связанного Participant отсутствует Payment со статусом `paid`.

Без оплаты сервер возвращает:

```text
409 Conflict
```

```json
{
  "detail": "Registration fee must be paid before confirmation"
}
```

После создания Payment со статусом `paid` заявка может быть подтверждена.

## Технологии

* Python;
* FastAPI;
* SQLAlchemy;
* PostgreSQL;
* Alembic;
* Pydantic;
* pytest;
* Ruff;
* HTML;
* CSS;
* JavaScript;
* Git;
* GitHub.

## Основные сущности
Учётная запись хранится в отдельной сущности `User`.

`User` не связан внешним ключом с `Participant`.

```text
Participant
│
├── Application
├── Invitation
├── Payment
├── Thesis
└── HotelRequest
```

`Report` отдельной таблицей не является. Он формируется динамически на основании существующих данных.

## Установка

### 1. Клонировать репозиторий

```powershell
git clone https://github.com/Ekaterinakokonina200/conference_DevOps.git
cd conference_DevOps
```

### 2. Создать виртуальное окружение

```powershell
python -m venv .venv
```

Активировать:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Установить зависимости

```powershell
python -m pip install -r requirements.txt
```

### 4. Создать локальную конфигурацию

```powershell
Copy-Item .env.example .env
notepad .env
```

Пример:

```env
DATABASE_URL=postgresql://postgres:LOCAL_PASSWORD@localhost:5432/conference
```

Вместо `LOCAL_PASSWORD` необходимо указать локальный пароль PostgreSQL.

Файл `.env` нельзя добавлять в Git.

### 5. Применить миграции

```powershell
alembic upgrade head
```

Проверить:

```powershell
alembic current
alembic heads
```

Последняя миграция:

```text
c027a5eb74d0
```

### 6. Запустить приложение

```powershell
python -m uvicorn app.main:app --reload
```

## Адреса приложения

| Назначение    | Адрес                                 |
| ------------- | ------------------------------------- |
| Web-интерфейс | http://127.0.0.1:8000/                |
| Swagger       | http://127.0.0.1:8000/docs            |
| Health Check  | http://127.0.0.1:8000/health          |
| Сводный отчёт | http://127.0.0.1:8000/reports/summary |

## Аутентификация

| Метод | Маршрут | Назначение |
|---|---|---|
| `POST` | `/auth/register` | Регистрация |
| `POST` | `/auth/login` | Получение JWT |
| `GET` | `/auth/me` | Получение текущего пользователя |

`POST /auth/login` принимает
`application/x-www-form-urlencoded`.

Для `/auth/me` используется:

```http
Authorization: Bearer <JWT>

## Проверки

Перед созданием Pull Request необходимо выполнить:

```powershell
ruff check .
python -m pytest -v
git diff --check
alembic current
alembic heads
```
Ожидается успешное выполнение 16 тестов.

Результат `collected 0 items` не считается успешным.

## Документация проекта

Подробная документация проекта разделена по тематическим файлам:

| Документ                                                 | Содержание                                                  |
| -------------------------------------------------------- | ----------------------------------------------------------- |
| [Техническое задание](docs/technical-specification.md)   | Назначение, требования и функциональные возможности системы |
| [Схема данных](docs/data-schema.md)                      | ER-диаграмма, таблицы, поля, ключи и связи между сущностями |
| [HTTP API](docs/api.md)                                  | Описание HTTP-методов, адресов, параметров и ответов        |
| [Правила внесения изменений](docs/contribution-rules.md) | Git-процесс, правила коммитов, Pull Request и приёмки       |
| [Ручное тестирование](docs/manual-testing.md)            | Последовательность ручной проверки приложения               |
| [Разрешение merge conflict](docs/merge-conflict.md)      | Описание создания и ручного разрешения конфликта Git        |

Все документы отображаются непосредственно на GitHub в режиме **Preview**. Файл со схемой данных содержит визуальную ER-диаграмму, которая строится средствами Mermaid.


## Git-процесс

Изменения проходят следующий путь:

```text
GitHub Issue
→ отдельная ветка
→ осмысленные коммиты
→ Ruff и pytest
→ Pull Request
→ review другого участника
→ Approve
→ merge в main
```

Прямые коммиты в `main` запрещены.

## Команда проекта

* Коконина Екатерина Олеговна;
* Баранова Мария Григорьевна;
* Отхонова Амуланга Александровна.

## Версия

Первая завершённая версия проекта отмечается Git-тегом:

```text
v0.1.0
```
