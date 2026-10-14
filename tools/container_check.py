"""Автоматическая проверка контейнерного окружения (make container-check).

Окружение принимается, только если выполнены ВСЕ эксплуатационные требования
(docs/container-rules.md). Проверка работает в отдельном проекте Compose
conference_check (свои контейнеры, сеть, том, порт 18000), поэтому рабочее
окружение участника (make up) не затрагивается. Пароли для проверки
генерируются заново при каждом запуске, после проверки всё удаляется.

Шаги:
  1. правила окружения — Dockerfile, .dockerignore и compose.yaml без запуска:
     образы с версией и дайджестом (без latest), USER не root, нет секретов
     в образе и в compose.yaml, healthcheck не отключён, опубликован только
     разрешённый порт и только на 127.0.0.1, ограничения ресурсов у всех;
  2. сборка образа и запуск db -> migrate -> app, ожидание healthy;
  3. пользователи процессов: в app — только UID 10001, в db — не root;
  4. приложение отвечает, миграции применены до последней версии;
  5. секретов нет в образе (история слоёв, переменные, файлы .env);
  6. данные сохраняются после пересоздания контейнеров и после обновления образа;
  7. корректное завершение по SIGTERM: код 0, быстрее stop_grace_period;
  8. резервная копия и восстановление БД в новый том;
  9. потребление ресурсов ниже установленных ограничений.

Запуск:  make container-check            полная проверка (3–6 минут)
         make container-policy           только шаг 1 (несколько секунд)
         make container-check keep=1     не удалять окружение проверки
"""

import json
import re
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# Обоснование: импорт после sys.path.insert — скрипт запускается как файл.
from container_db import Compose, backup, counts, restore_new_volume  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
ENV_FILE = ROOT / ".env.check"
PROJECT = "conference_check"
PORT = 18000
VOLUME = "conference_check_pgdata"
RESTORED_VOLUME = "conference_check_restored"
APP_UID = "10001"

# Какие сервисы могут публиковать порты наружу и какие именно (порт в контейнере).
# Добавление нового опубликованного порта — только через Pull Request
# с изменением этого списка и docs/container-rules.md.
ALLOWED_PUBLISHED = {"app": {8000}, "nginx": {8080}}
ALLOWED_HOST_IP = "127.0.0.1"
# Имена переменных, в которых хранятся секреты (ACCESS_TOKEN_EXPIRE_MINUTES — нет)
SECRET_WORDS = re.compile(r"PASSWORD|SECRET|PRIVATE_KEY|API_KEY|(^|_)TOKEN$", re.I)
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")
GRACEFUL_LIMIT_S = 15
MEMORY_SHARE_LIMIT = 0.8

TOTAL_STEPS = 9
VERSIONS = ["check-1", "check-2"]
FIND_ENV_FILES = (
    "import pathlib; print([str(p) for p in pathlib.Path('/app').rglob('.env*')])"
)


class CheckFailed(Exception):
    pass


def step(number: int, title: str) -> None:
    print(f"\n[{number}/{TOTAL_STEPS}] {title}", flush=True)


def ok(text: str) -> None:
    print(f"  ok  {text}", flush=True)


def fail(text: str) -> None:
    raise CheckFailed(text)


def docker(*args: str, check: bool = True, input_bytes=None) -> str:
    result = subprocess.run(
        ["docker", *args], capture_output=True, input=input_bytes, cwd=ROOT
    )
    out = result.stdout.decode("utf-8", "replace")
    if check and result.returncode != 0:
        err = result.stderr.decode("utf-8", "replace").strip()
        fail(f"docker {' '.join(args)}: {err}")
    return out


# ---------------------------------------------------------------- шаг 1
def image_ref_problems(where: str, ref: str, built_here: bool) -> list[str]:
    problems = []
    name_tag = ref.split("@", 1)[0]
    last = name_tag.rsplit("/", 1)[-1]
    tag = last.split(":", 1)[1] if ":" in last else ""
    if not tag:
        problems.append(f"{where}: образ {ref} без версии (тега)")
    elif tag == "latest":
        problems.append(f"{where}: образ {ref} с тегом latest запрещён")
    if not built_here and not DIGEST.search(ref):
        problems.append(
            f"{where}: внешний образ {ref} не закреплён по дайджесту "
            "(выполните make pin-images)"
        )
    return problems


def dockerfile_problems() -> list[str]:
    problems = []
    lines = [
        line.strip()
        for line in (ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines()
    ]
    joined = "\n".join(lines).replace("\\\n", " ")
    instructions = [ln for ln in joined.splitlines() if ln and not ln.startswith("#")]

    froms = [ln.split()[1] for ln in instructions if ln.upper().startswith("FROM ")]
    stages = {
        ln.split()[-1].lower()
        for ln in instructions
        if ln.upper().startswith("FROM ") and " AS " in ln.upper()
    }
    if not froms:
        problems.append("Dockerfile: нет инструкции FROM")
    for ref in froms:
        if ref.lower() not in stages:
            problems.extend(image_ref_problems("Dockerfile FROM", ref, False))

    users = [
        ln.split(None, 1)[1] for ln in instructions if ln.upper().startswith("USER ")
    ]
    if not users:
        problems.append("Dockerfile: нет инструкции USER — процесс работал бы от root")
    elif users[-1].split(":")[0] in ("root", "0"):
        problems.append("Dockerfile: последний USER — root")

    health = [ln for ln in instructions if ln.upper().startswith("HEALTHCHECK")]
    if not health:
        problems.append("Dockerfile: нет HEALTHCHECK")
    elif any("NONE" in ln.upper().split()[1:2] for ln in health):
        problems.append("Dockerfile: HEALTHCHECK NONE отключает проверку состояния")

    for ln in instructions:
        word = ln.split(None, 1)[0].upper()
        if word in ("ENV", "ARG"):
            names = re.findall(r"([A-Za-z_][A-Za-z0-9_]*)=", ln) or ln.split()[1:2]
            for name in names:
                if SECRET_WORDS.search(name):
                    problems.append(f"Dockerfile: секрет {name} в образе запрещён")
        if word == "COPY" and re.search(r"\.env\b", ln):
            problems.append(f"Dockerfile: копирование .env в образ запрещено: {ln}")

    cmd = [ln for ln in instructions if ln.upper().startswith(("CMD", "ENTRYPOINT"))]
    if cmd and not cmd[-1].split(None, 1)[1].lstrip().startswith("["):
        problems.append(
            "Dockerfile: CMD/ENTRYPOINT в форме shell — приложение не получит SIGTERM"
        )
    return problems


def dockerignore_problems() -> list[str]:
    path = ROOT / ".dockerignore"
    if not path.exists():
        return [".dockerignore отсутствует"]
    rules = [
        ln.strip()
        for ln in path.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.startswith("#")
    ]
    problems = []
    if "*" not in rules:
        for pattern in (".env", ".env.*", ".git", "backups"):
            if pattern not in rules:
                problems.append(f".dockerignore: не исключено {pattern}")
    if any(r.startswith("!") and ".env" in r for r in rules):
        problems.append(".dockerignore: файлы .env явно разрешены (!) — запрещено")
    return problems


def compose_config(env_file: Path, files: list[str]) -> dict:
    args = ["compose", "--env-file", str(env_file)]
    for name in files:
        args += ["-f", name]
    return json.loads(docker(*args, "config", "--format", "json"))


def memory_bytes(value) -> int:
    if isinstance(value, int | float):
        return int(value)
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([kmg]?)i?b?", str(value).lower())
    if not match:
        return 0
    factor = {"": 1, "k": 1024, "m": 1024**2, "g": 1024**3}[match[2]]
    return int(float(match[1]) * factor)


def compose_problems(config: dict, raw_texts: dict[str, str]) -> list[str]:
    problems = []
    networks = config.get("networks", {})
    # образы, которые собираются из Dockerfile проекта (у сервиса есть build)
    project_images = {
        svc.get("image")
        for svc in config.get("services", {}).values()
        if "build" in svc
    }
    for name, svc in config.get("services", {}).items():
        where = f"compose: сервис {name}"
        built_here = "build" in svc or svc.get("image") in project_images
        image = svc.get("image", "")
        if not image:
            problems.append(f"{where}: не указан образ с версией (image)")
        else:
            problems.extend(image_ref_problems(where, image, built_here))

        health = svc.get("healthcheck")
        if health and (health.get("disable") or health.get("test") in (["NONE"],)):
            problems.append(f"{where}: healthcheck отключён — запрещено")
        if not health and not built_here:
            problems.append(f"{where}: нет healthcheck")

        user = str(svc.get("user", ""))
        if user.split(":")[0] in ("root", "0"):
            problems.append(f"{where}: запуск от root (user: {user}) запрещён")
        if svc.get("privileged"):
            problems.append(f"{where}: privileged: true запрещено")
        if svc.get("network_mode") == "host":
            problems.append(f"{where}: network_mode: host запрещено")

        allowed = ALLOWED_PUBLISHED.get(name, set())
        for port in svc.get("ports", []):
            target = int(port.get("target", 0))
            if target not in allowed:
                problems.append(
                    f"{where}: публикация порта {target} запрещена "
                    f"(разрешено: {sorted(allowed) or 'ничего'})"
                )
            elif port.get("host_ip") != ALLOWED_HOST_IP:
                problems.append(
                    f"{where}: порт {target} должен публиковаться только на "
                    f"{ALLOWED_HOST_IP}, а не на всех интерфейсах"
                )

        limits = svc.get("deploy", {}).get("resources", {}).get("limits", {})
        for key in ("cpus", "memory", "pids"):
            if not limits.get(key):
                problems.append(f"{where}: нет ограничения ресурсов {key}")

        if name == "db":
            for vol in svc.get("volumes", []):
                if vol.get("target", "").startswith("/var/lib/postgresql") and (
                    vol.get("type") != "volume"
                ):
                    problems.append(
                        f"{where}: данные БД должны быть в именованном томе"
                    )
            for net in svc.get("networks", {}):
                if not networks.get(net, {}).get("internal"):
                    problems.append(
                        f"{where}: БД подключена к неизолированной сети {net}"
                    )

    for file_name, text in raw_texts.items():
        for number, line in enumerate(text.splitlines(), 1):
            match = re.match(r"\s*-?\s*([A-Z_]+)\s*[:=]\s*(.+)", line)
            if (
                match
                and SECRET_WORDS.search(match[1])
                and "${" not in match[2]
                and not line.lstrip().startswith("#")
            ):
                problems.append(
                    f"{file_name}:{number}: секрет записан прямо в файле — "
                    "передавайте его через переменную ${...}"
                )
    return problems


def git_ignore_problems() -> list[str]:
    problems = []
    for name in (".env", ".env.docker", ".env.check"):
        result = subprocess.run(
            ["git", "check-ignore", "-q", name], cwd=ROOT, capture_output=True
        )
        if result.returncode != 0:
            problems.append(f".gitignore: файл {name} не исключён из Git")
    return problems


def compose_files() -> list[str]:
    return [name for name in ("compose.yaml",) if (ROOT / name).exists()]


def policy(env_file: Path) -> None:
    step(1, "Правила окружения (Dockerfile, .dockerignore, compose.yaml)")
    files = compose_files()
    config = compose_config(env_file, files)
    raw = {name: (ROOT / name).read_text(encoding="utf-8") for name in files}
    problems = (
        dockerfile_problems()
        + dockerignore_problems()
        + compose_problems(config, raw)
        + git_ignore_problems()
    )
    if problems:
        print("  Нарушены правила контейнерного окружения (docs/container-rules.md):")
        for problem in problems:
            print(f"    - {problem}")
        fail(f"нарушений правил: {len(problems)}")
    ok("образы с версией и дайджестом, не root, без секретов, healthcheck, порты,")
    ok("ограничения ресурсов, изоляция БД — правила соблюдены")


# ---------------------------------------------------------------- шаги 2–9
def write_env(version: str, volume: str = VOLUME) -> dict[str, str]:
    values = {
        "POSTGRES_DB": "conference",
        "POSTGRES_USER": "conference",
        "POSTGRES_PASSWORD": secrets.token_hex(24),
        "JWT_SECRET_KEY": secrets.token_hex(24),
        "APP_VERSION": version,
        "APP_PORT": str(PORT),
        "PGDATA_VOLUME": volume,
    }
    if ENV_FILE.exists():
        old = dict(
            line.split("=", 1)
            for line in ENV_FILE.read_text(encoding="utf-8").splitlines()
            if "=" in line
        )
        for key in ("POSTGRES_PASSWORD", "JWT_SECRET_KEY"):
            values[key] = old.get(key, values[key])
    ENV_FILE.write_text(
        "".join(f"{k}={v}\n" for k, v in values.items()), encoding="utf-8"
    )
    return values


def http(method: str, path: str, body=None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        f"http://127.0.0.1:{PORT}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        # Обоснование: адрес фиксированный (127.0.0.1), схема http задана в коде.
        with urllib.request.urlopen(request, timeout=10) as response:  # nosec B310
            return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as error:
        return error.code, None
    except OSError as error:
        return 0, str(error)


def wait_http(path: str = "/health", seconds: int = 60) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        status, _ = http("GET", path)
        if status == 200:
            return
        time.sleep(1)
    fail(f"приложение не отвечает на {path} по адресу 127.0.0.1:{PORT}")


def container_id(compose: Compose, service: str) -> str:
    out = compose.run("ps", "-a", "-q", service).stdout.decode().split()
    if not out:
        fail(f"контейнер сервиса {service} не найден")
    return out[0]


def up(compose: Compose) -> None:
    result = compose.run(
        "up", "-d", "--build", "--wait", "--wait-timeout", "240", "app", check=False
    )
    if result.returncode != 0:
        logs = compose.run("logs", "--tail", "40", check=False).stdout.decode(
            "utf-8", "replace"
        )
        fail(
            "окружение не запустилось или не стало healthy:\n"
            + result.stderr.decode("utf-8", "replace")[-1500:]
            + "\n"
            + logs[-3000:]
        )


def process_users(compose: Compose) -> None:
    step(3, "Пользователи процессов в контейнерах")
    script = (
        "import os\n"
        "for p in sorted(x for x in os.listdir('/proc') if x.isdigit()):\n"
        "    try:\n"
        "        s = open(f'/proc/{p}/status').read()\n"
        "        c = open(f'/proc/{p}/cmdline','rb').read()"
        ".replace(b'\\0', b' ').decode().replace('\\n', ' ')\n"
        "    except OSError:\n"
        "        continue\n"
        "    uid = [ln.split()[1] for ln in s.splitlines()"
        " if ln.startswith('Uid:')][0]\n"
        "    print(p, uid, c[:60])\n"
    )
    # скрипт передаётся через стандартный ввод (python -), а не аргументом -c:
    # иначе многострочный текст попадает в командную строку процесса
    out = compose.run(
        "exec", "-T", "app", "python", "-", input_bytes=script.encode()
    ).stdout.decode()
    # у процесса может не быть командной строки — дополняем до трёх полей
    rows = [
        (line.split(None, 2) + [""])[:3] for line in out.splitlines() if line.strip()
    ]
    bad = [r for r in rows if r[1] != APP_UID]
    if bad or not rows:
        fail(f"в контейнере app есть процессы не от UID {APP_UID}: {bad or 'нет'}")
    for pid, uid, cmd in rows:
        if "uvicorn" in cmd or pid == "1":
            ok(f"app: PID {pid} UID {uid}  {cmd.strip()}")
    status = compose.run("exec", "-T", "db", "cat", "/proc/1/status").stdout.decode()
    uid = [ln.split()[1] for ln in status.splitlines() if ln.startswith("Uid:")][0]
    if uid == "0":
        fail("в контейнере db главный процесс работает от root")
    ok(f"db:  PID 1 UID {uid} (postgres)")


def app_and_migrations(compose: Compose) -> None:
    step(4, "Приложение и миграции")
    wait_http()
    ok(f"GET http://127.0.0.1:{PORT}/health -> 200")
    out = compose.run("exec", "-T", "app", "alembic", "current").stdout.decode()
    if "(head)" not in out:
        fail(f"схема БД не на последней версии: {out.strip()}")
    ok(f"alembic current: {out.strip().splitlines()[-1]}")


def no_secrets_in_image(compose: Compose, env: dict[str, str]) -> None:
    step(5, "Секреты не попали в образ")
    image = f"conference-app:{env['APP_VERSION']}"
    info = json.loads(docker("image", "inspect", image))[0]["Config"]
    history = docker("history", "--no-trunc", "--format", "{{.CreatedBy}}", image)
    haystack = json.dumps(info) + history
    for key in ("POSTGRES_PASSWORD", "JWT_SECRET_KEY"):
        if env[key] in haystack:
            fail(f"значение {key} найдено в образе")
    if any(
        SECRET_WORDS.search(item.split("=", 1)[0]) for item in info.get("Env") or []
    ):
        fail(f"в переменных образа есть секреты: {info.get('Env')}")
    if str(info.get("User", "")).split(":")[0] != APP_UID:
        fail(f"пользователь образа {info.get('User')!r}, ожидается {APP_UID}")
    found = (
        compose.run(
            "exec",
            "-T",
            "app",
            "python",
            "-c",
            FIND_ENV_FILES,
        )
        .stdout.decode()
        .strip()
    )
    if found != "[]":
        fail(f"в образе есть файлы .env: {found}")
    ok("пароли и ключи не встречаются в слоях и переменных образа")
    ok(f"файлов .env в /app нет, пользователь образа {info.get('User')}")


def persistence(compose: Compose, env: dict[str, str]) -> tuple[str, str]:
    step(6, "Сохранность данных после пересоздания контейнеров и обновления образа")
    email = f"container-check-{secrets.token_hex(4)}@example.com"
    status, body = http(
        "POST",
        "/participants/",
        {"full_name": "Проверка контейнеров", "email": email},
    )
    if status != 201:
        fail(f"не удалось создать участника: {status} {body}")
    ok(f"создан участник {email}")

    compose.run("down")
    ok("docker compose down: контейнеры и сети удалены, том остался")
    up(compose)
    if not participant_exists(email):
        fail("после пересоздания контейнеров участник пропал")
    ok("после пересоздания контейнеров участник на месте")

    old_image = docker(
        "image", "inspect", "-f", "{{.Id}}", f"conference-app:{env['APP_VERSION']}"
    ).strip()
    new_env = write_env("check-2")
    up(compose)
    new_image = docker(
        "image", "inspect", "-f", "{{.Id}}", "conference-app:check-2"
    ).strip()
    running = docker(
        "inspect", "-f", "{{.Image}}", container_id(compose, "app")
    ).strip()
    if new_image == old_image or running != new_image:
        fail("контейнер app не пересоздан из нового образа")
    if not participant_exists(email):
        fail("после обновления образа участник пропал")
    ok("образ обновлён (check-1 -> check-2), контейнеры пересозданы, участник на месте")
    return email, new_env["APP_VERSION"]


def participant_exists(email: str) -> bool:
    wait_http()
    status, body = http("GET", "/participants/")
    return status == 200 and any(p.get("email") == email for p in body)


def graceful_stop(compose: Compose) -> None:
    step(7, "Корректное завершение по сигналу остановки (SIGTERM)")
    cid = container_id(compose, "app")
    started = time.time()
    compose.run("stop", "-t", "20", "app")
    seconds = time.time() - started
    code = docker("inspect", "-f", "{{.State.ExitCode}}", cid).strip()
    # uvicorn пишет журнал в stderr, поэтому собираем оба потока
    result = subprocess.run(
        ["docker", "logs", "--tail", "30", cid], capture_output=True
    )
    logs = (result.stdout + result.stderr).decode("utf-8", "replace")
    if code != "0":
        fail(f"контейнер завершился с кодом {code} (137 — убит по SIGKILL)")
    if seconds >= GRACEFUL_LIMIT_S:
        fail(f"остановка заняла {seconds:.1f} с — сигнал не обработан приложением")
    if "Finished server process" not in logs:
        fail("в журнале нет 'Finished server process' — uvicorn не завершился штатно")
    ok(f"код завершения 0 за {seconds:.1f} с, в журнале: Finished server process")
    up(compose)


def backup_restore(compose: Compose, email: str) -> Compose:
    step(8, "Резервная копия и восстановление БД в новый том")
    before = counts(compose)
    path = backup(compose, "_check", directory=REPORTS)
    new = restore_new_volume(compose, str(path), RESTORED_VOLUME)
    after = counts(new)
    if after != before:
        fail(f"после восстановления данные отличаются: было {before}, стало {after}")
    mounted = docker(
        "inspect", "-f", "{{range .Mounts}}{{.Name}} {{end}}", container_id(new, "db")
    )
    if RESTORED_VOLUME not in mounted:
        fail(f"БД работает не на новом томе: {mounted}")
    if not participant_exists(email):
        fail("после восстановления в новый том участник не найден через API")
    ok(f"БД восстановлена в новый том {RESTORED_VOLUME}, данные совпадают: {after}")
    return new


def resources(compose: Compose) -> None:
    step(9, "Потребление ресурсов ниже ограничений")
    for service in ("db", "app"):
        cid = container_id(compose, service)
        limit = int(docker("inspect", "-f", "{{.HostConfig.Memory}}", cid).strip())
        stats = docker(
            "stats", "--no-stream", "--format", "{{.MemUsage}};{{.CPUPerc}}", cid
        ).strip()
        usage_text, cpu = stats.split(";")
        usage = memory_bytes(usage_text.split("/")[0].strip())
        if not limit:
            fail(f"{service}: ограничение памяти не применено")
        share = usage / limit
        if share > MEMORY_SHARE_LIMIT:
            fail(f"{service}: память {usage_text} — больше {MEMORY_SHARE_LIMIT:.0%}")
        ok(f"{service}: память {usage_text.strip()} ({share:.0%} лимита), CPU {cpu}")


def cleanup(
    compose: Compose, versions: list[str], title: str = "Удаляю окружение проверки..."
) -> None:
    print(f"\n{title}", flush=True)
    for volume in (VOLUME, RESTORED_VOLUME):
        compose.with_env(PGDATA_VOLUME=volume).run(
            "down", "-v", "--remove-orphans", check=False
        )
        docker("volume", "rm", "-f", volume, check=False)
    for version in versions:
        docker("image", "rm", "-f", f"conference-app:{version}", check=False)
    ENV_FILE.unlink(missing_ok=True)


def run_checks(compose: Compose) -> None:
    """Шаги 2–9: окружение запускается в отдельном проекте conference_check."""
    cleanup(compose, VERSIONS, "Удаляю остатки прошлой проверки...")
    env = write_env("check-1")
    step(2, "Сборка образа и запуск окружения (db -> migrate -> app)")
    up(compose)
    ok("db и app — healthy, migrate завершился с кодом 0")
    process_users(compose)
    app_and_migrations(compose)
    no_secrets_in_image(compose, env)
    email, _ = persistence(compose, env)
    graceful_stop(compose)
    compose = backup_restore(compose, email)
    resources(compose)


def main() -> None:
    policy_only = "--policy-only" in sys.argv
    keep = "--keep" in sys.argv
    REPORTS.mkdir(exist_ok=True)
    write_env("check-1")
    compose = Compose(ENV_FILE, PROJECT)
    started = time.time()
    runtime_started = False
    try:
        policy(ENV_FILE)
        if policy_only:
            print("\ncontainer-policy: правила контейнерного окружения соблюдены")
            return
        runtime_started = True
        run_checks(compose)
    except (CheckFailed, SystemExit) as error:
        # SystemExit — ошибка внутри вспомогательных функций container_db
        print(f"\n  ОШИБКА: {error}")
        print("\ncontainer-check: окружение НЕ принято")
        sys.exit(1)
    finally:
        if runtime_started and not keep:
            cleanup(compose, VERSIONS)
        if not keep:
            ENV_FILE.unlink(missing_ok=True)
    minutes = (time.time() - started) / 60
    print(f"\ncontainer-check: контейнерное окружение принято ({minutes:.1f} мин)")


if __name__ == "__main__":
    main()
