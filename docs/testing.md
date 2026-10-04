# Тестовая конфигурация и изоляция тестовых данных

## Отдельная тестовая база

Тесты никогда не работают с рабочей базой `conference`. Для них используется
отдельная база `conference_test`, адрес которой задан в файле `.env.test`:

```env
TEST_DATABASE_URL=postgresql://postgres:<пароль>@localhost:5432/conference_test
```

Файл создаётся командой `make setup` из шаблона `.env.test.example` и в Git
не добавляется.

`tests/conftest.py` до импорта приложения подменяет переменные окружения:

| Переменная | Значение в тестах |
|---|---|
| `DATABASE_URL` | значение `TEST_DATABASE_URL` |
| `JWT_SECRET_KEY` | постоянный тестовый ключ (не секрет, только для тестов) |
| `JWT_ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` |

Защита от ошибки: если имя базы в `TEST_DATABASE_URL` не оканчивается на
`_test`, pytest останавливается до запуска тестов, потому что тесты удаляют
и пересоздают все таблицы.

## Изоляция данных

1. В начале прогона (`tests/integration/conftest.py`, фикстура
   `migrated_database`) схема тестовой базы удаляется и создаётся заново
   миграциями Alembic — тестируется та же схема, что будет на сервере.
2. Каждый интеграционный тест получает соединение с открытой транзакцией
   (фикстура `db_session`). Приложение внутри теста выполняет `commit`, но это
   фиксация вложенной точки сохранения (SAVEPOINT). После теста внешняя
   транзакция откатывается, и база снова пустая.
3. Фикстура `client` подменяет зависимость `get_db`, поэтому HTTP-запросы
   теста идут в ту же транзакцию.

Изоляцию проверяет `tests/integration/test_isolation.py`: первый тест создаёт
участника, второй убеждается, что база пустая.

## Структура тестов

| Каталог | Маркер | Что проверяется | База данных |
|---|---|---|---|
| `tests/unit` | `unit` | основная логика `app/services/rules.py`, схемы, хеширование и JWT | не нужна |
| `tests/integration` | `integration` | HTTP API вместе с PostgreSQL | `conference_test`, откат после каждого теста |
| `tests/migrations` | `migrations` | миграции на чистой и заполненной базе | `conference_test`, схема пересоздаётся |

Маркер ставится автоматически по каталогу.

## Запуск

```bash
make test                # unit + integration, покрытие и отчёты
make migrations-check    # только миграции
.venv/Scripts/python -m pytest tests/integration/test_payments.py -q   # один файл (Windows)
```

## Отчёты

| Файл | Содержимое |
|---|---|
| `reports/junit.xml` | результаты тестов в формате JUnit |
| `reports/htmlcov/index.html` | покрытие кода по строкам и ветвлениям |
| `reports/coverage.xml` | покрытие в формате Cobertura |
| `reports/bandit.html` | отчёт SAST |

Каталог `reports/` создаётся заново при каждой проверке и в Git не хранится.
