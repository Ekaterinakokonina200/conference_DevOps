# Проверка на защите ЛР №2

| № | Проверка | Кто | Команды | Ожидается |
|---|---|---|---|---|
| 1 | Перезагрузка обеих машин и автоматический запуск | Коконина — перезагрузка; Баранова, Отхонова — проверка | sudo reboot; затем systemctl is-active postgresql@16-main, systemctl is-active conference, curl -s http://127.0.0.1:8000/reports/summary | службы active без ручного запуска, адреса сохранились |
| 2 | Остановка БД и диагностика приложения | Баранова — sudo systemctl stop postgresql; Отхонова — диагностика | curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/health и /reports/summary, sudo journalctl -u conference -n 30 --no-pager, nc -zv 192.168.56.11 5432 | /health → 200, /reports/summary → 500, в журнале Connection refused; после sudo systemctl start postgresql → 200 |
| 3 | Поиск процесса, порта и журналов | Отхонова (приложение), Баранова (БД) | pgrep -a -u conference, sudo ss -ltnp, sudo journalctl -u conference -n 50 --no-pager, sudo tail /var/log/postgresql/postgresql-16-main.log | процесс uvicorn от conference, порт 8000; postgres на 5432 |
| 4 | Изменение параметра службы и восстановление | Отхонова | drop-in RestartSec=15, systemctl daemon-reload, systemctl show conference -p RestartUSec; восстановление systemctl revert conference | было 5s, стало 15s, после восстановления снова 5s |
| 5 | Сетевая недоступность БД с постороннего узла | Баранова | Windows: Test-NetConnection 192.168.56.11 -Port 5432; сервер приложения: nc -zv 192.168.56.11 5432 | с Windows False, с сервера приложения succeeded |
| 6 | SSH только по ключам, root запрещён | Коконина | ssh app-katy "whoami", ssh -o PubkeyAuthentication=no katy@192.168.56.10, ssh root@192.168.56.10 | первое пускает, остальные Permission denied (publickey) |
| 7 | Приложение не от root, лишние порты закрыты | Отхонова | systemctl show conference -p User, sudo ss -ltnp, sudo ufw status numbered | User=conference; открыты только 22 и 8000 |
| 8 | Пароли не в репозитории | Баранова | git ls-files \| grep -Ei '(^\|/)\.env$\|conference\.env$\|id_ed25519' | пусто; в репозитории только .env.example и deploy/conference.env.example |
| 9 | Путь изменения через ветку и PR | любой | GitHub: Issues, Pull requests, история main | у каждого PR есть Approve другого участника |
