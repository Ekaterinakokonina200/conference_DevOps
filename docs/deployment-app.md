# Развёртывание: сервер приложения и systemd

Ответственный: Отхонова А.А. (Участник №3).

Сервер: `conference-app`, `192.168.56.10`, Ubuntu Server 24.04, Python 3.12.
Приложение: FastAPI + uvicorn, порт 8000. БД: PostgreSQL на `192.168.56.11`.

## 1. Пользователь службы

Приложение работает от системного пользователя `conference`: без пароля, без `sudo`, с оболочкой `/usr/sbin/nologin`. Войти под ним нельзя, запуск от root исключён.

## 2. Размещение и права

| Путь | Владелец:группа | Права | Смысл |
|---|---|---|---|
| `/opt/conference/app` | `root:conference` | каталоги `750`, файлы `640` | код и venv; служба читает, но не может изменить |
| `/etc/conference/conference.env` | `root:conference` | `640` | настройки и секреты вне репозитория |
| `/etc/systemd/system/conference.service` | `root:root` | `644` | описание службы |

## 3. Настройки вне кода

Шаблон — `deploy/conference.env.example`. Рабочий файл — `/etc/conference/conference.env`:

```env
DATABASE_URL=postgresql://conference_app:<пароль>@192.168.56.11:5432/conference
JWT_SECRET_KEY=<вывод openssl rand -hex 32>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Правила:

* каждая настройка — на отдельной строке;
* без кавычек и без пробелов вокруг `=`;
* файл не добавляется в Git — он лежит вне каталога репозитория.

Проверка скрытых символов (строки с секретами отфильтрованы):

```bash
sudo cat -A /etc/conference/conference.env | grep -v "^DATABASE_URL\|^JWT_SECRET_KEY"
```

Каждая строка должна заканчиваться `$` сразу после значения. Если две строки склеены (например, `JWT_ALGORITHM=HS256 ACCESS_TOKEN_EXPIRE_MINUTES=30`), вход в приложение падает с ошибкой `Algorithm not supported`.

## 4. Развёртывание и обновление

```bash
sudo bash scripts/deploy-app.sh
sudo bash scripts/setup-app-firewall.sh
```

`deploy-app.sh`:

1. устанавливает Python и зависимости;
2. создаёт пользователя `conference`;
3. клонирует или обновляет код (`git pull`);
4. создаёт venv и ставит пакеты из `requirements.txt`;
5. проверяет `conference.env`;
6. выставляет права;
7. применяет миграции Alembic;
8. устанавливает unit-файл из `deploy/conference.service`;
9. включает и перезапускает службу.

При первом запуске скрипт создаёт `conference.env` из шаблона и останавливается: нужно заполнить пароль и секрет и запустить скрипт снова.

## 5. systemd

| Строка | Зачем |
|---|---|
| `User=conference` | процесс работает не от root |
| `WorkingDirectory=/opt/conference/app` | приложение находит `app/static` |
| `EnvironmentFile=/etc/conference/conference.env` | настройки из файла вне репозитория |
| `Restart=on-failure`, `RestartSec=5` | после аварии служба поднимается через 5 секунд |
| `StartLimitBurst=5` за 60 с | нет бесконечных перезапусков |
| `WantedBy=multi-user.target` | автозапуск при загрузке |
| `NoNewPrivileges`, `ProtectSystem`, `ProtectHome`, `PrivateTmp` | ограничения процесса |

Управление:

```bash
sudo systemctl start|stop|restart conference
systemctl status conference --no-pager
systemctl is-enabled conference
sudo journalctl -u conference -n 50 --no-pager
```

`journalctl` выполняется через `sudo`: без него администратор не видит журнал службы.

## 6. Автоматический перезапуск

```bash
sudo kill -9 $(systemctl show -p MainPID --value conference)
sleep 6
systemctl show conference -p MainPID -p NRestarts
```

Служба снова `active` с новым `MainPID`, `NRestarts` увеличился.

## 7. Firewall

| Порт | Откуда разрешён |
|---|---|
| 22/tcp | `192.168.56.0/24` |
| 8000/tcp | `192.168.56.0/24` |

## 8. Проверки

```bash
curl -s http://127.0.0.1:8000/health            # {"status":"ok"}
curl -s http://127.0.0.1:8000/reports/summary   # JSON; проверяет связь с БД
```

С Windows: `http://192.168.56.10:8000/` (веб-интерфейс), `http://192.168.56.10:8000/docs` (Swagger).

`/health` не обращается к БД. Связь с БД проверяется через `/reports/summary`: при остановленной БД он возвращает 500, а в журнале — `Connection refused`.

## 9. Частые ошибки

| Симптом | Причина | Решение |
|---|---|---|
| `DATABASE_URL is not configured` | служба не читает `conference.env` | путь в `EnvironmentFile`, права `640 root:conference` |
| `password authentication failed` | неверный пароль в `DATABASE_URL` | исправить файл, перезапустить службу |
| `Algorithm not supported` при входе | склеены строки в `conference.env` | проверить `cat -A`, одна настройка на строку |
| `/reports/summary` → 500 | нет связи с БД | `nc -zv 192.168.56.11 5432`, firewall и `pg_hba.conf` на сервере БД |
| `-- No entries --` в `journalctl` | нет прав на журнал | `sudo journalctl ...` |
