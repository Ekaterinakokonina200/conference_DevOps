# Conference Management System

Система управления участниками научной конференции.

Проект разработан в рамках лабораторных работ №1 «Сквозной проект и Git-процесс», №2 «Развёртывание приложения в Linux-среде» и №3 «Автоматические проверки, миграции и резервное копирование».

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

Нужны: Git (с Git Bash), Python 3.12, PostgreSQL (локально), GNU make.
Команды выполняются в Git Bash (в VS Code: терминал Git Bash).

```bash
git clone https://github.com/Ekaterinakokonina200/conference_DevOps.git
cd conference_DevOps
make setup
```

`make setup` — единый сценарий первоначальной настройки (`tools/setup_project.py`):

1. создаёт виртуальное окружение `.venv` и ставит зафиксированные версии
   зависимостей из `requirements-dev.txt`;
2. создаёт `.env` и `.env.test` из шаблонов и генерирует `JWT_SECRET_KEY`;
3. останавливается и просит вписать пароль PostgreSQL, если его нет;
4. проверяет наличие `psql`, `pg_dump`, `pg_restore`;
5. создаёт базы `conference` и `conference_test`;
6. применяет миграции к рабочей базе.

После того как пароль вписан, `make setup` запускают ещё раз. Файлы `.env`
и `.env.test` в Git не добавляются.

Запуск приложения:

```bash
make run
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

## Проверки (локальный проверочный контур)

Любое изменение попадает в `main` только после успешного `make verify`
(правила — в [docs/quality-rules.md](docs/quality-rules.md)).

```bash
make verify
```

| Шаг | Команда | Что проверяет |
|---|---|---|
| 1 | `make format-check` | код отформатирован по единому стилю (`ruff format --check`) |
| 2 | `make lint` | линтер `ruff check`: ошибки, стиль PEP 8, порядок импортов, типичные ошибки |
| 3 | `make sast` | статический анализ безопасности `bandit`: отчёт в терминале и в `reports/bandit.html`, `reports/bandit.txt`; `make sast-report` открывает HTML-отчёт в браузере |
| 4 | `make rules-check` | нет пропущенных тестов, порогов ниже минимума, исключений без обоснования, незафиксированных версий |
| 5 | `make test` | unit- и интеграционные тесты на тестовой базе, покрытие не ниже порога, отчёты `reports/` |
| 6 | `make migrations-check` | миграции на чистой и заполненной базе, откат, совпадение моделей и схемы |
| 7 | `make backup-check` | резервная копия → порча данных → восстановление → сравнение |
| 8 | `make mutation` | мутационная проверка: тесты замечают изменение любого условия основной логики |

Команда `make quality` запускает шаги 1–3 (форматирование и статический
анализ). Перед созданием PR выполните `make critical-changes` — он покажет,
изменены ли критические файлы приёмки (`.github/CODEOWNERS`); такие
изменения требуют Approve владельца файла.

Остальные команды — `make help`.

## Непрерывная интеграция (CI)

[![CI](https://github.com/Ekaterinakokonina200/conference_DevOps/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Ekaterinakokonina200/conference_DevOps/actions/workflows/ci.yml)

GitHub Actions (`.github/workflows/ci.yml`) при каждом push и Pull Request
выполняет те же команды, что и локальный контур: стиль, правила, безопасность
(bandit, gitleaks, trivy), тесты на отдельной БД, миграции, резервное
копирование, `make container-check`, сборку и анализ образа. Образ с тегом
commit SHA публикуется в `ghcr.io/ekaterinakokonina200/conference-app` только
из `main` и только если прошли все проверки. Подробнее — [docs/ci.md](docs/ci.md).

Все проверки CI локально (нужен Docker):

```bash
make ci-local
```

| Команда | Что проверяет |
|---|---|
| `make secrets-scan` | секреты в истории Git (gitleaks) |
| `make deps-scan` | уязвимости зависимостей (trivy) |
| `make image-scan` | уязвимости контейнерного образа (trivy) |
| `make security` | `sast` + `secrets-scan` + `deps-scan` |

## Запуск в контейнерах (Docker)

Нужен Docker Desktop (Windows) или Docker Engine с Compose v2.

```bash
make container-env   # один раз: .env.docker со случайными паролями
make up              # сборка образа, запуск db -> migrate -> app
```

Приложение: <http://127.0.0.1:8000>. Порт базы данных наружу не публикуется.

| Команда | Назначение |
|---|---|
| `make up` / `make down` | запуск / остановка (данные остаются в томе `conference_pgdata`) |
| `make ps`, `make logs s=app` | состояние и журналы |
| `make container-migrate` | миграции |
| `make container-backup` | резервная копия БД из контейнера |
| `make container-restore file=latest` | восстановление в текущий том |
| `make container-restore-new file=latest volume=ИМЯ` | восстановление в новый том |
| `make container-check` | **обязательная** проверка контейнерного окружения перед Pull Request |

Правила контейнерного окружения — [docs/container-rules.md](docs/container-rules.md).

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
| [Сеть и SSH](docs/deployment-network-ssh.md)             | Адреса, администраторы, SSH-ключи, запрет root              |
| [Сервер БД](docs/deployment-database.md)                 | PostgreSQL, минимальные права, firewall                     |
| [Приложение и systemd](docs/deployment-app.md)           | Развёртывание, настройки вне кода, служба                   |
| [Проверка на защите](docs/deployment-checklist.md)       | Чек-лист проверок ЛР №2                                     |
| [Правила качества](docs/quality-rules.md)                | Проверочный контур, запреты, журнал исключений              |
| [Тестирование](docs/testing.md)                          | Тестовая конфигурация, изоляция данных, отчёты              |
| [Покрытие ТЗ тестами](docs/test-coverage.md)             | Матрица «требование ТЗ — тесты», граничные случаи           |
| [Миграции и резервные копии](docs/database-maintenance.md) | Миграции, backup, restore, проверка на заполненной БД     |
| [Контейнерное окружение](docs/container.md)              | Образ, Compose, сети, том, backup/restore в контейнерах     |
| [Правила контейнеров](docs/container-rules.md)           | Запреты и `make container-check`, порядок изменений         |
| [Ограничения ресурсов](docs/container-resources.md)      | Лимиты CPU, памяти и процессов, обоснование и измерения     |
| [Непрерывная интеграция](docs/ci.md)                     | Pipeline GitHub Actions, секреты, публикация образа, защита |

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

Версия с локальным проверочным контуром (ЛР №3):

```text
v0.3.0
```

Версия с контейнерным окружением и автоматической проверкой (ЛР №4):


```text
v0.4.0
```
