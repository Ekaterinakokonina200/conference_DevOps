"""Создание файла настроек контейнерного окружения (make container-env).

Копирует .env.docker.example в .env.docker и заменяет каждое значение
GENERATE_RANDOM на случайную строку (пароль БД, секрет JWT). Секреты
появляются только на компьютере участника и в Git не попадают
(.env.docker закрыт в .gitignore). Существующий .env.docker не меняется.
"""

import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / ".env.docker.example"
TARGET = ROOT / ".env.docker"
PLACEHOLDER = "GENERATE_RANDOM"


def main() -> None:
    if TARGET.exists():
        print(".env.docker уже есть — не изменяю")
        return
    lines = []
    for line in TEMPLATE.read_text(encoding="utf-8").splitlines():
        if line.endswith("=" + PLACEHOLDER):
            line = line.replace(PLACEHOLDER, secrets.token_hex(24))
        lines.append(line)
    TARGET.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(".env.docker создан, пароль БД и секрет JWT сгенерированы")


if __name__ == "__main__":
    main()
