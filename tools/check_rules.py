"""Проверка правил качества (make rules-check).

Правила описаны в docs/quality-rules.md. Скрипт не даёт незаметно:
- пропускать тесты (skip, skipif, xfail, importorskip);
- отключать замечания линтера и SAST без обоснования (noqa, nosec и т. п.);
- снижать порог покрытия и добавлять исключения анализаторов без записи
  в журнал исключений docs/quality-rules.md;
- убирать шаги из make verify;
- ставить зависимости без фиксированной версии.
"""

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Минимальные значения. Повышать можно, понижать — только через PR
# с записью в журнале исключений docs/quality-rules.md.
MIN_COVERAGE = 90
REQUIRED_VERIFY_STEPS = [
    "format-check",
    "lint",
    "sast",
    "rules-check",
    "test",
    "migrations-check",
    "backup-check",
    "mutation",
]
REQUIRED_PYTEST_OPTIONS = ["--strict-markers", "--strict-config"]

SKIP_PATTERNS = re.compile(
    r"pytest\.mark\.(skip|skipif|xfail)\b|pytest\.(skip|xfail|importorskip)\("
    r"|unittest\.skip"
)
SUPPRESS_PATTERNS = re.compile(
    r"#\s*(noqa|nosec|type:\s*ignore|pragma:\s*no\s*cover)", re.IGNORECASE
)
JUSTIFICATION = "обоснование:"
CHECKED_DIRS = ["app", "tests", "alembic", "tools"]

errors: list[str] = []


def python_files():
    for folder in CHECKED_DIRS:
        for path in sorted((ROOT / folder).rglob("*.py")):
            if path.resolve() != Path(__file__).resolve():
                yield path


def check_tests_not_skipped() -> None:
    for path in sorted((ROOT / "tests").rglob("*.py")):
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        for number, line in enumerate(lines, 1):
            if SKIP_PATTERNS.search(line):
                errors.append(
                    f"{path.relative_to(ROOT)}:{number}: пропуск теста запрещён"
                )


def check_suppressions_justified() -> None:
    for path in python_files():
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        for index, line in enumerate(lines):
            if not SUPPRESS_PATTERNS.search(line):
                continue
            previous = lines[index - 1] if index > 0 else ""
            if JUSTIFICATION in line.lower() or JUSTIFICATION in previous.lower():
                continue
            errors.append(
                f"{path.relative_to(ROOT)}:{index + 1}: отключение проверки "
                "без комментария «Обоснование: …» на этой или предыдущей строке"
            )


def check_config() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    tool = config["tool"]
    journal = (ROOT / "docs" / "quality-rules.md").read_text(encoding="utf-8")

    fail_under = tool["coverage"]["report"].get("fail_under", 0)
    if fail_under < MIN_COVERAGE:
        errors.append(
            f"pyproject.toml: порог покрытия {fail_under}% ниже "
            f"минимального {MIN_COVERAGE}%"
        )

    addopts = tool["pytest"]["ini_options"].get("addopts", "")
    for option in REQUIRED_PYTEST_OPTIONS:
        if option not in addopts:
            errors.append(f"pyproject.toml: в addopts pytest нет {option}")
    for option in ("--deselect", "--ignore", "-k "):
        if option in addopts:
            errors.append(f"pyproject.toml: {option} в addopts отключает тесты")

    lint = tool["ruff"]["lint"]
    exceptions = list(lint.get("ignore", []))
    for codes in lint.get("per-file-ignores", {}).values():
        exceptions.extend(codes)
    exceptions.extend(tool.get("bandit", {}).get("skips", []))
    for code in exceptions:
        if f"`{code}`" not in journal:
            errors.append(
                f"pyproject.toml: исключение {code} не описано в журнале "
                "исключений docs/quality-rules.md"
            )


def check_verify_steps() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    match = re.search(r"^verify:(.*)$", makefile, re.MULTILINE)
    steps = match.group(1).split() if match else []
    for step in REQUIRED_VERIFY_STEPS:
        if step not in steps:
            errors.append(f"Makefile: в make verify нет обязательного шага {step}")


def check_pinned_requirements() -> None:
    for name in ("requirements.txt", "requirements-dev.txt"):
        lines = (ROOT / name).read_text(encoding="utf-8").splitlines()
        for number, raw in enumerate(lines, 1):
            line = raw.split("#")[0].strip()
            if not line or line.startswith("-r "):
                continue
            if "==" not in line:
                errors.append(f"{name}:{number}: версия не зафиксирована (нужно ==)")


def main() -> None:
    check_tests_not_skipped()
    check_suppressions_justified()
    check_config()
    check_verify_steps()
    check_pinned_requirements()
    if errors:
        print("Нарушены правила качества (docs/quality-rules.md):")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    print("rules-check: правила качества соблюдены")


if __name__ == "__main__":
    main()
