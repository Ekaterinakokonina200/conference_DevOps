"""Проверка правил качества (make rules-check).

Правила описаны в docs/quality-rules.md. Скрипт не даёт незаметно:
- пропускать тесты (skip, skipif, xfail, importorskip);
- отключать замечания линтера и SAST без обоснования (noqa, nosec и т. п.);
- снижать порог покрытия и добавлять исключения анализаторов без записи
  в журнал исключений docs/quality-rules.md;
- убирать шаги из make verify и удалять проверку make container-check;
- ставить зависимости без фиксированной версии;
- удалять тесты (число тестовых функций не меньше MIN_TEST_FUNCTIONS);
- ослаблять pipeline CI (.github/workflows/ci.yml): убирать задания и команды,
  разрешать падение проверки, публиковать образ без всех проверок,
  использовать действия без закрепления по SHA и пароли в открытом виде;
- добавлять исключения сканеров безопасности (.trivyignore, .gitleaksignore)
  без обоснования.
"""

import ast
import re
import sys
import tomllib
from pathlib import Path

import yaml

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
# Число тестовых функций в tests/ (ЛР №5). Удалить тест незаметно нельзя:
# уменьшить это число можно только изменением этого файла (CODEOWNERS)
# с записью в журнале исключений docs/quality-rules.md.
MIN_TEST_FUNCTIONS = 124

# Pipeline CI: обязательные задания и команды make в них (ЛР №5)
CI_WORKFLOW = ".github/workflows/ci.yml"
REQUIRED_CI_JOBS = {
    "style": ["make format-check", "make lint"],
    "rules": ["make rules-check"],
    "security": ["make sast", "make secrets-scan", "make deps-scan"],
    "tests": ["make test", "make mutation"],
    "migrations": ["make migrations-check"],
    "backup": ["make backup-check"],
    "build": ["make image-scan"],
}
PUBLISH_JOB = "publish"
SCANNER_IGNORE_FILES = [".trivyignore", ".gitleaksignore"]

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


def check_container_check() -> None:
    """make container-check обязателен для изменений контейнерного окружения."""
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    match = re.search(r"^container-check:.*\n\t(.*)$", makefile, re.MULTILINE)
    if not match or "tools/container_check.py" not in match.group(1):
        errors.append("Makefile: нет команды container-check (container_check.py)")
    if "--policy-only" in (match.group(1) if match else ""):
        errors.append("Makefile: container-check ограничен только правилами")


def check_pinned_requirements() -> None:
    for name in ("requirements.txt", "requirements-dev.txt"):
        lines = (ROOT / name).read_text(encoding="utf-8").splitlines()
        for number, raw in enumerate(lines, 1):
            line = raw.split("#")[0].strip()
            if not line or line.startswith("-r "):
                continue
            if "==" not in line:
                errors.append(f"{name}:{number}: версия не зафиксирована (нужно ==)")


def check_test_count() -> None:
    count = 0
    for path in sorted((ROOT / "tests").rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        count += sum(
            1
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        )
    if count < MIN_TEST_FUNCTIONS:
        errors.append(
            f"tests/: тестовых функций {count}, меньше минимума "
            f"{MIN_TEST_FUNCTIONS} — удаление тестов запрещено"
        )


def run_commands(job: dict) -> str:
    return "\n".join(str(step.get("run", "")) for step in job.get("steps", []))


def check_ci_workflow() -> None:
    """Pipeline CI нельзя незаметно ослабить (docs/quality-rules.md, раздел 5)."""
    path = ROOT / CI_WORKFLOW
    if not path.exists():
        errors.append(f"{CI_WORKFLOW}: нет файла pipeline CI")
        return
    text = path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    # PyYAML читает ключ on: как True
    triggers = workflow.get("on", workflow.get(True)) or {}
    for event in ("push", "pull_request"):
        if event not in triggers:
            errors.append(f"{CI_WORKFLOW}: CI не запускается при событии {event}")
    jobs = workflow.get("jobs", {})
    for name, commands in REQUIRED_CI_JOBS.items():
        job = jobs.get(name)
        if job is None:
            errors.append(f"{CI_WORKFLOW}: нет обязательного задания {name}")
            continue
        runs = run_commands(job)
        for command in commands:
            if not re.search(rf"(^|\s){re.escape(command)}(\s|$)", runs, re.M):
                errors.append(f"{CI_WORKFLOW}: в задании {name} нет «{command}»")
    for name, job in jobs.items():
        where = f"{CI_WORKFLOW}: задание {name}"
        if job.get("continue-on-error") or str(job.get("if", "")).strip() == "false":
            errors.append(
                f"{where}: проверка отключена (continue-on-error / if: false)"
            )
        for step in job.get("steps", []):
            label = step.get("name") or step.get("uses") or step.get("run", "")[:30]
            if step.get("continue-on-error"):
                errors.append(f"{where}, шаг «{label}»: continue-on-error запрещён")
            if str(step.get("if", "")).strip() == "false":
                errors.append(f"{where}, шаг «{label}»: шаг отключён (if: false)")
            uses = step.get("uses", "")
            if uses and not re.search(r"@[0-9a-f]{40}$", uses):
                errors.append(f"{where}: действие {uses} не закреплено по commit SHA")
            if re.search(r"\|\|\s*(true|exit 0)|;\s*exit 0", str(step.get("run", ""))):
                errors.append(f"{where}, шаг «{label}»: ошибка команды подавлена")
    publish = jobs.get(PUBLISH_JOB)
    if publish is None:
        errors.append(f"{CI_WORKFLOW}: нет задания {PUBLISH_JOB}")
    else:
        needs = publish.get("needs", [])
        needs = [needs] if isinstance(needs, str) else needs
        for name in REQUIRED_CI_JOBS:
            if name not in needs:
                errors.append(
                    f"{CI_WORKFLOW}: {PUBLISH_JOB} публикует образ без задания {name}"
                )
        if "always()" in str(publish.get("if", "")):
            errors.append(f"{CI_WORKFLOW}: {PUBLISH_JOB} запускается при ошибках")
    if "github.sha" not in text:
        errors.append(f"{CI_WORKFLOW}: тег образа не связан с commit SHA")
    for number, line in enumerate(text.splitlines(), 1):
        match = re.match(r"\s*([A-Z_]*(PASSWORD|TOKEN|SECRET)[A-Z_]*):\s*(.+)", line)
        if match and "secrets." not in match.group(3):
            errors.append(
                f"{CI_WORKFLOW}:{number}: {match.group(1)} не из защищённых "
                "переменных (secrets)"
            )


def check_scanner_ignores() -> None:
    """Исключения сканеров безопасности — только с обоснованием."""
    for name in SCANNER_IGNORE_FILES:
        path = ROOT / name
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            previous = lines[index - 1] if index > 0 else ""
            if JUSTIFICATION not in previous.lower():
                errors.append(
                    f"{name}:{index + 1}: исключение без комментария "
                    "«# Обоснование: …» на предыдущей строке"
                )


def main() -> None:
    check_tests_not_skipped()
    check_suppressions_justified()
    check_config()
    check_verify_steps()
    check_container_check()
    check_pinned_requirements()
    check_test_count()
    check_ci_workflow()
    check_scanner_ignores()
    if errors:
        print("Нарушены правила качества (docs/quality-rules.md):")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    print("rules-check: правила качества соблюдены")


if __name__ == "__main__":
    main()
