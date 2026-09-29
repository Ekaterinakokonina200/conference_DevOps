# Развёртывание: сервер базы данных

Ответственный: Баранова М.Г. (Участник №2).

Сервер: conference-db, 192.168.56.11, Ubuntu Server 24.04, PostgreSQL 16.

## 1. Установка и настройка

sudo bash scripts/setup-database.sh

Скрипт:

1. устанавливает PostgreSQL;
2. создаёт роль conference_app (пароль вводится с клавиатуры и не сохраняется в истории команд);
3. создаёт базу conference, владелец — conference_app;
4. отзывает права на базу у PUBLIC;
5. задаёт listen_addresses = 'localhost,192.168.56.11';
6. добавляет в pg_hba.conf правило, разрешающее подключение только с сервера приложения;
7. перезапускает PostgreSQL.

Правило в pg_hba.conf:

host    conference    conference_app    192.168.56.10/32    scram-sha-256

Пароль: только латинские буквы и цифры (символы @ : / ? # ломают строку DATABASE_URL). Пароль передаётся ответственному за приложение лично и в репозиторий не добавляется.

## 2. Минимальные права

sudo -u postgres psql -P pager=off -c "\du conference_app"
sudo -u postgres psql -P pager=off -c "\l conference"

* у conference_app нет атрибутов Superuser, Create role, Create DB;
* роль — владелец только своей базы: это нужно миграциям Alembic, которые создают в ней таблицы;
* к другим базам роль подключиться не может.

## 3. Firewall

sudo bash scripts/setup-db-firewall.sh

| Порт | Откуда разрешён |
|---|---|
| 22/tcp | 192.168.56.0/24 |
| 5432/tcp | только 192.168.56.10 |

Остальные входящие подключения запрещены.

## 4. Проверки

На сервере БД:

sudo ss -ltnp | grep 5432      # LISTEN на 127.0.0.1 и 192.168.56.11, без 0.0.0.0
sudo ufw status verbose

С сервера приложения:

nc -zv 192.168.56.11 5432                                                             # succeeded
psql -h 192.168.56.11 -U conference_app -d conference -c "SELECT current_user;"        # conference_app
psql -h 192.168.56.11 -U conference_app -d postgres -c "SELECT 1;"                     # no pg_hba.conf entry
psql -h 192.168.56.11 -U conference_app -d conference -c "CREATE DATABASE test_rights;" # permission denied

С постороннего узла (Windows):

Test-NetConnection -ComputerName 192.168.56.11 -Port 5432   # TcpTestSucceeded : False

## 5. Диагностика

systemctl status postgresql@16-main --no-pager
sudo tail -n 20 /var/log/postgresql/postgresql-16-main.log
sudo -u postgres psql -P pager=off -d conference -c "\dt"

-P pager=off отключает постраничный просмотр. Если вывод всё же открылся в просмотрщике, выйти клавишей q.

После внезапного выключения ВМ PostgreSQL восстанавливается сам (в журнале — database system was interrupted и redo done).
