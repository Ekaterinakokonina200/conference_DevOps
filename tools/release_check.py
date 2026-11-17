"""Проверка работающего релиза (ЛР №6): make release-check, deploy/staging/deploy.sh.

Успешная сборка ещё не успешный релиз: версия принимается, только если в
целевой среде прошли все пять проверок.

  1. Контейнеры: db и app запущены, healthcheck = healthy, app не
     перезапускался и работает из ожидаемого образа (если задан --project).
  2. Служебный адрес: GET /health -> 200 {"status": "ok"}.
  3. Версия: GET /version -> ожидаемые version и revision (commit SHA).
  4. Веб-интерфейс: GET / -> 200, страница с формой регистрации.
  5. Основной пользовательский сценарий через API: участник -> заявка ->
     подтверждение без оплаты отклонено (409) -> оплата -> заявка подтверждена.
     Созданные проверкой данные удаляются.

Скрипт использует только стандартную библиотеку Python: он запускается и на
компьютере участника (make release-check против make up), и на сервере
предэксплуатационного окружения, где нет виртуального окружения проекта.

Код выхода 0 — релиз принят, 1 — релиз не принят (печатается причина).
"""

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

TOTAL_STEPS = 5


class ReleaseCheckFailed(Exception):
    pass


def step(number: int, title: str) -> None:
    print(f"\n[{number}/{TOTAL_STEPS}] {title}", flush=True)


def ok(text: str) -> None:
    print(f"  ok  {text}", flush=True)


def fail(text: str) -> None:
    raise ReleaseCheckFailed(text)


class Client:
    def __init__(self, base_url: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(self, method: str, path: str, body=None) -> tuple[int, str]:
        if not self.base_url.startswith(("http://", "https://")):
            fail(f"адрес должен начинаться с http:// или https://: {self.base_url}")
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        # Схема адреса проверена выше (только http/https), адрес целевой среды
        # задаёт оператор, а не пользователь приложения.
        try:
            # Обоснование: urlopen только для http/https адреса целевой среды
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:  # nosec B310
                return resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode("utf-8", "replace")
        except OSError as error:
            fail(f"{method} {path}: нет ответа от {self.base_url} ({error})")
        return 0, ""

    def json(self, method: str, path: str, body=None, expect: int = 200):
        status, text = self.request(method, path, body)
        if status != expect:
            fail(f"{method} {path} -> {status}, ожидался {expect}: {text[:200]}")
        try:
            return json.loads(text) if text else None
        except json.JSONDecodeError:
            fail(f"{method} {path}: ответ не JSON: {text[:200]}")


def docker_json(*args: str) -> list[dict]:
    try:
        result = subprocess.run(["docker", *args], capture_output=True, check=False)
    except FileNotFoundError:
        fail("не найден docker")
    if result.returncode != 0:
        message = result.stderr.decode(errors="replace").strip()
        fail(f"docker {' '.join(args)}: {message}")
    return json.loads(result.stdout.decode() or "[]")


def check_containers(project: str, expect_image: str | None) -> None:
    step(1, f"Контейнеры (проект {project})")
    label = f"label=com.docker.compose.project={project}"
    ids = (
        subprocess.run(
            ["docker", "ps", "-aq", "--filter", label],
            capture_output=True,
            check=False,
        )
        .stdout.decode()
        .split()
    )
    if not ids:
        fail(f"нет контейнеров проекта {project}")
    containers = {}
    for item in docker_json("inspect", *ids):
        service = item["Config"]["Labels"].get("com.docker.compose.service", "?")
        containers.setdefault(service, item)
    for service in ("db", "app"):
        item = containers.get(service)
        if item is None:
            fail(f"нет контейнера {service}")
        state = item["State"]
        health = (state.get("Health") or {}).get("Status", "нет healthcheck")
        if state.get("Status") != "running":
            fail(f"{service}: состояние {state.get('Status')}, ожидалось running")
        if health != "healthy":
            fail(f"{service}: healthcheck {health}, ожидалось healthy")
        if item.get("RestartCount", 0):
            fail(f"{service}: контейнер перезапускался {item['RestartCount']} раз")
        ok(f"{service}: running, healthy, перезапусков 0")
    image = containers["app"]["Config"]["Image"]
    if expect_image and image != expect_image:
        fail(f"app работает из образа {image}, ожидался {expect_image}")
    ok(f"app: образ {image}")


def check_health(client: Client, number: int) -> None:
    step(number, "Служебный адрес /health")
    body = client.json("GET", "/health")
    if body != {"status": "ok"}:
        fail(f"/health вернул {body}, ожидалось {{'status': 'ok'}}")
    ok("GET /health -> 200 {'status': 'ok'}")


def check_version(
    client: Client, number: int, version: str | None, revision: str | None
) -> None:
    step(number, "Работающая версия /version")
    body = client.json("GET", "/version")
    print(
        f"  version={body.get('version')}  revision={body.get('revision')}  "
        f"instance={body.get('instance')}"
    )
    if version and body.get("version") != version:
        fail(f"работает версия {body.get('version')}, ожидалась {version}")
    if revision and body.get("revision") != revision:
        fail(f"работает коммит {body.get('revision')}, ожидался {revision}")
    ok("версия и коммит совпадают с развёрнутым образом")


def check_web(client: Client, number: int) -> None:
    step(number, "Веб-интерфейс /")
    status, text = client.request("GET", "/")
    if status != 200:
        fail(f"GET / -> {status}: веб-интерфейс не открывается")
    if 'id="register-form"' not in text:
        fail("GET /: на странице нет формы регистрации (id=register-form)")
    ok("GET / -> 200, страница с формой регистрации")


def check_scenario(client: Client, number: int) -> None:
    step(number, "Основной сценарий: участник -> заявка -> оплата -> подтверждение")
    email = f"release-check-{int(time.time())}-{uuid.uuid4().hex[:6]}@example.com"
    participant = client.json(
        "POST",
        "/participants/",
        {
            "full_name": "Проверка Релиза",
            "email": email,
            "organization": "release-check",
        },
        expect=201,
    )
    ok(f"участник создан (id={participant['id']}, {email})")
    try:
        application = client.json(
            "POST", "/applications/", {"participant_id": participant["id"]}, expect=201
        )
        if application.get("status") != "pending":
            status = application.get("status")
            fail(f"новая заявка в статусе {status}, ожидался pending")
        ok(f"заявка создана (id={application['id']}, status=pending)")
        path = f"/applications/{application['id']}"
        client.json("PUT", path, {"status": "confirmed"}, expect=409)
        ok("подтверждение без оплаты отклонено (409)")
        client.json(
            "POST",
            "/payments/",
            {"participant_id": participant["id"], "amount": 1500, "status": "paid"},
            expect=201,
        )
        ok("оплата 1500 зарегистрирована (status=paid)")
        confirmed = client.json("PUT", path, {"status": "confirmed"})
        if confirmed.get("status") != "confirmed":
            fail(f"после оплаты заявка в статусе {confirmed.get('status')}")
        ok("после оплаты заявка подтверждена (status=confirmed)")
    finally:
        status, _ = client.request("DELETE", f"/participants/{participant['id']}")
        if status == 204:
            print("  данные проверки удалены")
        else:
            print(f"  предупреждение: не удалось удалить участника проверки ({status})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--url", default="http://127.0.0.1:8000", help="адрес приложения"
    )
    parser.add_argument(
        "--project", help="проект Docker Compose для проверки контейнеров"
    )
    parser.add_argument("--expect-image", help="образ, из которого должен работать app")
    parser.add_argument("--expect-version", help="ожидаемая версия (/version)")
    parser.add_argument("--expect-revision", help="ожидаемый commit SHA (/version)")
    parser.add_argument("--timeout", type=float, default=10, help="тайм-аут запроса, с")
    args = parser.parse_args()

    client = Client(args.url, args.timeout)
    print(f"Проверка релиза: {args.url}")
    try:
        if args.project:
            check_containers(args.project, args.expect_image)
        else:
            step(1, "Контейнеры")
            print("  пропущено: не задан --project")
        check_health(client, 2)
        check_version(client, 3, args.expect_version, args.expect_revision)
        check_web(client, 4)
        check_scenario(client, 5)
    except ReleaseCheckFailed as error:
        print(f"\n  ОШИБКА  {error}")
        print("\nrelease-check: РЕЛИЗ НЕ ПРИНЯТ")
        return 1
    print("\nrelease-check: релиз принят — все проверки пройдены")
    return 0


if __name__ == "__main__":
    sys.exit(main())
