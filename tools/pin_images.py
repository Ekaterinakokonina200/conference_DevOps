"""Закрепление внешних образов по дайджесту (make pin-images).

Тег вроде python:3.12.10-slim-bookworm издатель может перезаписать
(например, пересобрать с обновлениями ОС). Дайджест sha256 — отпечаток
конкретного содержимого: образ name:tag@sha256:... всегда один и тот же.

Скрипт находит в Dockerfile и файлах Compose ссылки на внешние образы
(строки FROM ... и image: ...), скачивает каждый образ (docker pull),
узнаёт его дайджест и записывает ссылку в виде name:tag@sha256:<дайджест>.
Образы проекта (conference-app:${APP_VERSION}) не трогаются.

Уже закреплённые образы не меняются: обновить дайджест (например, ради
исправлений безопасности базового образа) можно только явно — отдельным
Pull Request с прогоном make container-check:
    make pin-images              закрепить образы без дайджеста (PIN_ME)
    make pin-images update=1     перезакрепить все образы на свежие дайджесты
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ["Dockerfile", "compose.yaml", "compose.scale.yaml"]

# FROM name:tag[@sha256:...]  или  image: name:tag[@sha256:...]
IMAGE_LINE = re.compile(
    r"^(?P<prefix>\s*(?:FROM\s+|image:\s*))"
    r"(?P<name>[a-z0-9][a-z0-9._/-]*):(?P<tag>[A-Za-z0-9._-]+)"
    r"(?:@(?P<digest>sha256:(?:[0-9a-f]{64}|PIN_ME)))?",
    re.MULTILINE,
)


def run(*args: str) -> str:
    result = subprocess.run(args, capture_output=True, text=True, errors="replace")
    if result.returncode != 0:
        sys.exit(f"Ошибка: {' '.join(args)}\n{result.stderr.strip()}")
    return result.stdout.strip()


def digest_of(name: str, tag: str) -> str:
    ref = f"{name}:{tag}"
    print(f"  docker pull {ref}")
    run("docker", "pull", "--quiet", ref)
    repo_digest = run(
        "docker", "image", "inspect", "--format", "{{index .RepoDigests 0}}", ref
    )
    if "@sha256:" not in repo_digest:
        sys.exit(f"Ошибка: не удалось получить дайджест образа {ref}")
    return repo_digest.split("@", 1)[1]


def main() -> None:
    update = "--update" in sys.argv
    cache: dict[str, str] = {}
    for file_name in FILES:
        path = ROOT / file_name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")

        def pin(match: re.Match) -> str:
            name, tag = match["name"], match["tag"]
            key = f"{name}:{tag}"
            current = match["digest"]
            if current and current != "sha256:PIN_ME" and not update:
                return match.group(0)
            if key not in cache:
                cache[key] = digest_of(name, tag)
            return f"{match['prefix']}{key}@{cache[key]}"

        new_text = IMAGE_LINE.sub(pin, text)
        if new_text != text:
            path.write_text(new_text, encoding="utf-8", newline="\n")
            print(f"{file_name}: образы закреплены по дайджесту")
        else:
            print(f"{file_name}: без изменений")
    for key, digest in sorted(cache.items()):
        print(f"  {key}@{digest}")


if __name__ == "__main__":
    main()
