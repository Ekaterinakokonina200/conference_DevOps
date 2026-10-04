# Миграции, резервное копирование и восстановление

## Миграции

Схема базы данных меняется только миграциями Alembic (`alembic/versions`).

| № | Ревизия | Изменение | Версия |
|---|---|---|---|
| 1 | `b683525bba83` | таблица participants | v0.1.0 |
| 2 | `883de5d6b956` | таблица applications | v0.1.0 |
| 3 | `27a4af35d848` | таблица invitations | v0.1.0 |
| 4 | `626aa6d0e2b7` | таблица payments | v0.1.0 |
| 5 | `1afdb60487ff` | таблица theses | v0.1.0 |
| 6 | `1dbb1a8d5df8` | таблица hotel_requests | v0.1.0 |
| 7 | `c027a5eb74d0` | таблица users | v0.1.0 |
| 8 | `d4f8a1c2b3e5` | CHECK-ограничения статусов и суммы оплаты; приведение старых статусов к допустимым | v0.3.0 |
| 9 | `e7b9c3d5f6a1` | ON DELETE CASCADE и индексы для participant_id | v0.3.0 |

Команды:

```bash
make migrate                    # применить все миграции к рабочей базе
make migrate-down               # откатить последнюю миграцию
make migration m="описание"     # создать новую миграцию (autogenerate)
make migrations-check           # проверка миграций на тестовой базе
```

Правила:

* миграция, меняющая существующие данные, сначала приводит их к допустимому
  виду, а потом добавляет ограничения (так миграции проходят на заполненной
  базе);
* финансовые данные миграция не исправляет молча: если в `payments` есть
  `amount <= 0`, миграция 8 останавливается с сообщением, и запись
  исправляют вручную;
* у каждой миграции есть `downgrade`;
* модели в `app/models` должны совпадать со схемой после миграций — это
  проверяет `alembic check` в `make migrations-check`.

`make migrations-check` (`tests/migrations/test_migrations.py`) проверяет:

| Тест | Что доказывает |
|---|---|
| `test_migrations_have_single_head` | нет параллельных веток миграций |
| `test_upgrade_clean_database` | пустая база создаётся миграциями, модели совпадают со схемой |
| `test_upgrade_filled_database_keeps_data` | база версии v0.1.0 с данными обновляется, данные сохраняются, «грязные» статусы исправляются |
| `test_upgrade_refuses_to_hide_bad_payments` | некорректные оплаты останавливают миграцию, база остаётся на прежней версии |
| `test_constraints_reject_invalid_data` | база сама отклоняет недопустимые значения |
| `test_deleting_participant_cascades_to_related_rows` | удаление участника удаляет связанные записи |
| `test_downgrade_to_v010_and_upgrade_again` | миграции откатываются и применяются повторно |

## Резервное копирование

```bash
make backup
```

Создаёт `backups/conference_ГГГГММДД-ЧЧММСС.dump` утилитой `pg_dump` в формате
custom (схема, данные и таблица `alembic_version`). После создания архив
проверяется командой `pg_restore --list`. Пароль передаётся утилитам через
переменную `PGPASSWORD`, а не в командной строке. Каталог `backups/` в Git
не добавляется.

## Восстановление

```bash
make restore file=backups/conference_20261002-153000.dump
make restore file=latest        # самая свежая копия
```

Перед восстановлением текущее состояние автоматически сохраняется в
`backups/..._before-restore.dump`, поэтому ошибочное восстановление можно
отменить. `pg_restore` запускается с `--clean --if-exists --single-transaction
--exit-on-error`: таблицы пересоздаются, а при любой ошибке база остаётся
в исходном состоянии. После восстановления выводится число записей в таблицах.

## Автоматическая проверка

`make backup-check` на тестовой базе выполняет сценарий: миграции → данные →
резервная копия → порча (удаление оплат, изменение имён) → восстановление →
сравнение содержимого всех таблиц с исходным.

## Сервер базы данных (стенд ЛР №2)

На сервере `conference-db` копия создаётся от имени `postgres`:

```bash
sudo -u postgres pg_dump --format=custom --file=/var/backups/conference_$(date +%Y%m%d-%H%M%S).dump conference
sudo -u postgres pg_restore --clean --if-exists --single-transaction --dbname=conference /var/backups/<файл>.dump
```

Копию делают перед каждым обновлением приложения, которое применяет миграции.
