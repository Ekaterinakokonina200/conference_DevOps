"""Проверка Nginx и нескольких экземпляров приложения (make scale-check).

Дополнительное задание ЛР №4. Окружение запускается из compose.yaml
и compose.scale.yaml (make up-scale), затем проверяется:
  1. прямого доступа к приложению нет (порт APP_PORT закрыт);
  2. запросы через Nginx распределяются между экземплярами;
  3. при остановке одного экземпляра сервис продолжает отвечать;
  4. ограничение частоты: при всплеске запросов Nginx отвечает 429.
"""

import collections
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env.docker"
COMPOSE = [
    "docker", "compose", "--env-file", str(ENV_FILE),
    "-f", "compose.yaml", "-f", "compose.scale.yaml",
]  # fmt: skip


def setting(name: str, default: str) -> str:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip()
    return default


NGINX = f"http://127.0.0.1:{setting('NGINX_PORT', '8080')}"
APP_PORT = int(setting("APP_PORT", "8000"))


def compose(*args: str) -> str:
    result = subprocess.run([*COMPOSE, *args], cwd=ROOT, capture_output=True)
    if result.returncode != 0:
        sys.exit(result.stderr.decode("utf-8", "replace"))
    return result.stdout.decode("utf-8", "replace")


def get(path: str):
    try:
        # Обоснование: адрес фиксированный (127.0.0.1), схема http задана в коде.
        with urllib.request.urlopen(NGINX + path, timeout=10) as resp:  # nosec B310
            return resp.status, json.loads(resp.read()), resp.headers.get("X-Upstream")
    except urllib.error.HTTPError as error:
        # заголовок X-Upstream есть и в ответе с ошибкой — видно, куда ходил Nginx
        return error.code, None, error.headers.get("X-Upstream")
    except OSError:
        return 0, None, None


def distribution(count: int) -> collections.Counter:
    seen = collections.Counter()
    for _ in range(count):
        status, body, upstream = get("/version")
        seen[(status, body["instance"] if body else "-", upstream)] += 1
        time.sleep(0.05)
    return seen


def health(container: str) -> str:
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Health.Status}}", container],
        capture_output=True,
    )
    return result.stdout.decode().strip()


def start_and_wait(containers: list[str]) -> None:
    """Запустить остановленные экземпляры и дождаться healthy."""
    for container in containers:
        subprocess.run(["docker", "start", container], capture_output=True, check=True)
    deadline = time.monotonic() + 90
    while any(health(c) != "healthy" for c in containers):
        if time.monotonic() > deadline:
            sys.exit(f"  ОШИБКА: экземпляры не стали healthy: {containers}")
        time.sleep(2)
    # Nginx переразрешает имя app раз в 10 секунд (resolver valid=10s)
    time.sleep(12)


def ensure_all_running() -> None:
    """Все экземпляры app должны работать (прерванная проверка могла
    оставить один остановленным)."""
    all_ids = compose("ps", "-a", "-q", "app").split()
    running = set(compose("ps", "-q", "app").split())
    if len(all_ids) < 2:
        sys.exit("  ОШИБКА: экземпляров app меньше двух — выполните make up-scale")
    stopped = [c for c in all_ids if c not in running]
    if stopped:
        names = ", ".join(c[:12] for c in stopped)
        print(f"  запускаю остановленные экземпляры: {names}")
        start_and_wait(stopped)


def show(seen: collections.Counter) -> None:
    for (status, instance, upstream), number in sorted(seen.items()):
        print(f"    {number:3} ответов {status} от экземпляра {instance} ({upstream})")


def main() -> None:
    if not ENV_FILE.exists():
        sys.exit("Нет .env.docker — выполните make container-env.")
    print("1. Прямой доступ к приложению")
    with socket.socket() as sock:
        sock.settimeout(2)
        if sock.connect_ex(("127.0.0.1", APP_PORT)) == 0:
            sys.exit(
                f"  ОШИБКА: порт приложения {APP_PORT} открыт — доступ в обход Nginx"
            )
    print(f"  порт {APP_PORT} закрыт, приложение доступно только через Nginx")

    print("2. Распределение запросов (20 запросов GET /version через Nginx)")
    ensure_all_running()
    seen = distribution(20)
    show(seen)
    instances = {instance for (status, instance, _) in seen if status == 200}
    if len(instances) < 2:
        sys.exit("  ОШИБКА: запросы обработал меньше чем 2 экземпляра")

    print("3. Остановка одного экземпляра")
    ids = compose("ps", "-q", "app").split()
    stopped = ids[0]
    subprocess.run(["docker", "stop", stopped], capture_output=True, check=True)
    print(f"  остановлен контейнер {stopped[:12]}")
    try:
        seen = distribution(20)
        show(seen)
        if any(status != 200 for (status, _, _) in seen):
            sys.exit("  ОШИБКА: после остановки экземпляра были неуспешные ответы")
        print("  все 20 запросов успешны — сервис доступен")
    finally:
        # экземпляр запускается снова при любом исходе, даже при ошибке или Ctrl+C
        start_and_wait([stopped])
        print(f"  контейнер {stopped[:12]} запущен снова")

    print("4. Ограничение частоты (100 запросов без паузы)")
    codes = collections.Counter(get("/health")[0] for _ in range(100))
    print(f"    ответы: {dict(codes)}")
    if not codes.get(429):
        sys.exit("  ОШИБКА: Nginx не ограничил частоту запросов")

    print("\nscale-check: балансировка и отказоустойчивость подтверждены")


if __name__ == "__main__":
    main()
