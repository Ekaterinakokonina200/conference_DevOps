"""Изменённые критические файлы приёмки (make critical-changes).

Сравнивает текущую ветку с origin/main и показывает, какие из изменённых
файлов перечислены в .github/CODEOWNERS. Вывод вставляется в описание
Pull Request, чтобы проверяющий отдельно посмотрел эти файлы.

Пример: make critical-changes            (сравнение с origin/main)
        make critical-changes base=main
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_rules() -> list[tuple[str, list[str]]]:
    rules = []
    for line in (
        (ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8").splitlines()
    ):
        line = line.strip()
        if line and not line.startswith("#"):
            pattern, *owners = line.split()
            rules.append((pattern.lstrip("/"), owners))
    return rules


def owners_of(path: str, rules) -> list[str] | None:
    found = None
    for pattern, owners in rules:  # как в GitHub: побеждает последнее совпадение
        if path == pattern or (pattern.endswith("/") and path.startswith(pattern)):
            found = owners
    return found


def changed_files(base: str) -> list[str]:
    committed = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    local = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    return sorted(set(committed) | {line[3:].strip('"') for line in local})


def main() -> None:
    base = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else "origin/main"
    rules = read_rules()
    critical = [
        (path, owners_of(path, rules))
        for path in changed_files(base)
        if owners_of(path, rules)
    ]
    if not critical:
        print(f"Критические файлы приёмки не изменены (сравнение с {base}).")
        return
    print(f"Изменены критические файлы приёмки (сравнение с {base}):")
    for path, owners in critical:
        print(f"  - {path}  (владельцы: {', '.join(owners)})")
    print("Опишите в PR, зачем изменён каждый файл; нужен Approve владельца.")


if __name__ == "__main__":
    main()
