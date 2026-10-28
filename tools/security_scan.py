"""Проверки безопасности, которые выполняются в контейнерах (ЛР №5).

    make secrets-scan   поиск секретов в истории Git (gitleaks)
    make deps-scan      уязвимости зависимостей requirements.txt (trivy)
    make image-scan     уязвимости контейнерного образа приложения (trivy)

Инструменты запускаются из образов, закреплённых по дайджесту в
docker/security-tools.yaml, — локально и в CI одинаково, поэтому результаты
совпадают. Отчёты сохраняются в reports/ (gitleaks.json, trivy-deps.json,
trivy-image.json и текстовые сводки *.txt).

Политика (docs/quality-rules.md, раздел «Непрерывная интеграция»):
  * найден хотя бы один секрет — ошибка;
  * уязвимость важности HIGH или CRITICAL, для которой выпущено исправление,
    — ошибка (обновить версию пакета или базового образа);
  * исключение — только строкой в .trivyignore с комментарием «# Обоснование: …»
    над ней (проверяет make rules-check).
"""

import argparse
import collections
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
CACHE = ROOT / ".cache"
TOOLS_FILE = ROOT / "docker" / "security-tools.yaml"
SKIP_DIRS = (
    ".venv,.git,reports,backups,.cache,.pytest_cache,.ruff_cache,.mutation_backup"
)
BLOCKING = ("CRITICAL", "HIGH")
LEVELS = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN")
NAMES = {
    "CRITICAL": "критическая",
    "HIGH": "высокая",
    "MEDIUM": "средняя",
    "LOW": "низкая",
    "UNKNOWN": "не указана",
}


def tool_image(name: str) -> str:
    """Ссылка на образ инструмента из docker/security-tools.yaml."""
    text = TOOLS_FILE.read_text(encoding="utf-8")
    match = re.search(rf"^{name}:\s*\n(?:\s*#.*\n)*\s*image:\s*(\S+)", text, re.M)
    if not match:
        sys.exit(f"В {TOOLS_FILE.relative_to(ROOT)} нет образа {name}")
    image = match.group(1)
    if "@sha256:" not in image or image.endswith("PIN_ME"):
        sys.exit(
            f"Образ {name} не закреплён по дайджесту ({image}). "
            "Выполните make pin-images."
        )
    return image


def docker_run(image: str, *args: str, extra: tuple[str, ...] = ()) -> int:
    if not shutil.which("docker"):
        sys.exit(
            "Не найден docker. Запустите Docker Desktop (локально) или Docker (CI)."
        )
    cmd = ["docker", "run", "--rm", "-v", f"{ROOT}:/src", "-w", "/src", *extra]
    if hasattr(os, "getuid"):  # Linux, CI: файлы отчётов принадлежат пользователю
        cmd += ["--user", f"{os.getuid()}:{os.getgid()}"]
    return subprocess.run([*cmd, image, *args], check=False).returncode


def write_summary(name: str, lines: list[str]) -> None:
    text = "\n".join(lines)
    (REPORTS / name).write_text(text + "\n", encoding="utf-8")
    print(text)


# ------------------------------------------------------------------ секреты
def secrets() -> int:
    image = tool_image("gitleaks")
    report = REPORTS / "gitleaks.json"
    report.unlink(missing_ok=True)
    # git внутри контейнера: каталог /src принадлежит другому пользователю
    git_env = (
        "-e", "GIT_CONFIG_COUNT=1",
        "-e", "GIT_CONFIG_KEY_0=safe.directory",
        "-e", "GIT_CONFIG_VALUE_0=*",
    )  # fmt: skip
    common = ("--no-banner", "--redact", "--exit-code", "0")
    docker_run(
        image, "git", *common, "--report-format", "json",
        "--report-path", "/src/reports/gitleaks.json", "/src", extra=git_env,
    )  # fmt: skip
    if not report.exists():
        sys.exit("gitleaks не создал отчёт reports/gitleaks.json")
    findings = json.loads(report.read_text(encoding="utf-8") or "[]")

    # Незакоммиченные изменения (git diff и git add) — только локально
    local = []
    if not os.getenv("CI"):
        for mode in ("--pre-commit", "--staged"):
            path = REPORTS / f"gitleaks{mode.replace('--', '-')}.json"
            path.unlink(missing_ok=True)
            docker_run(
                image, "git", mode, *common, "--report-format", "json",
                "--report-path", f"/src/reports/{path.name}", "/src", extra=git_env,
            )  # fmt: skip
            if path.exists():
                local += json.loads(path.read_text(encoding="utf-8") or "[]")

    lines = [
        "gitleaks — поиск секретов (пароли, токены, ключи) во всей истории Git",
        f"  найдено в коммитах: {len(findings)}",
    ]
    for item in findings:
        lines.append(
            f"    {item['File']}:{item['StartLine']}  правило {item['RuleID']}  "
            f"коммит {item['Commit'][:8]} ({item.get('Author', '')})"
        )
    if not os.getenv("CI"):
        lines.append(f"  найдено в незакоммиченных изменениях: {len(local)}")
        for item in local:
            lines.append(
                f"    {item['File']}:{item['StartLine']}  правило {item['RuleID']}"
            )
    total = len(findings) + len(local)
    lines += [
        "  значения секретов в отчёте скрыты (--redact)",
        "  отчёт: reports/gitleaks.json",
        "",
        "secrets-scan: секретов не найдено"
        if not total
        else f"secrets-scan: найдено секретов: {total} — удалить, сменить пароль/токен",
    ]
    write_summary("gitleaks.txt", lines)
    return 1 if total else 0


# ------------------------------------------------------------------ уязвимости
def trivy(*args: str) -> None:
    (CACHE / "trivy").mkdir(parents=True, exist_ok=True)
    code = docker_run(
        tool_image("trivy"), *args, "--cache-dir", "/src/.cache/trivy",
        "--scanners", "vuln", "--format", "json", "--quiet",
    )  # fmt: skip
    if code != 0:
        sys.exit(f"trivy завершился с ошибкой (код {code})")


def vulnerability_report(title: str, json_name: str, txt_name: str, gate: str) -> int:
    data = json.loads((REPORTS / json_name).read_text(encoding="utf-8"))
    vulns = []
    for result in data.get("Results") or []:
        for vuln in result.get("Vulnerabilities") or []:
            vulns.append((result.get("Target", ""), vuln))
    counts = collections.Counter()
    for _, vuln in vulns:
        fixed = "fix" if vuln.get("FixedVersion") else "nofix"
        counts[(vuln.get("Severity", "UNKNOWN"), fixed)] += 1
    blocking = [
        (target, v)
        for target, v in vulns
        if v.get("Severity") in BLOCKING and v.get("FixedVersion")
    ]
    lines = [
        title,
        "  политика: останавливают уязвимости важности CRITICAL и HIGH, "
        "для которых выпущено исправление",
        "",
        "    важность         с исправлением   без исправления   всего",
    ]
    for level in LEVELS:
        fix, nofix = counts[(level, "fix")], counts[(level, "nofix")]
        lines.append(f"    {NAMES[level]:<16}{fix:>15}{nofix:>18}{fix + nofix:>8}")
    lines.append(f"    {'всего':<16}{'':>15}{'':>18}{len(vulns):>8}")
    if blocking:
        lines += ["", f"  Блокирующие уязвимости: {len(blocking)}"]
    for target, v in sorted(
        blocking, key=lambda t: (t[1]["Severity"], t[1]["PkgName"])
    ):
        lines.append(
            f"    {v['VulnerabilityID']}  {NAMES[v['Severity']]}  {v['PkgName']} "
            f"{v.get('InstalledVersion', '')} -> исправлено в {v['FixedVersion']}"
            f"  ({target})"
        )
        lines.append(f"      {(v.get('Title') or '')[:100]}")
    lines += [
        "",
        f"  отчёт: reports/{json_name}, сводка: reports/{txt_name}",
        "",
        f"{gate}: блокирующих уязвимостей нет"
        if not blocking
        else f"{gate}: блокирующих уязвимостей {len(blocking)} — обновить версии",
    ]
    write_summary(txt_name, lines)
    return 1 if blocking else 0


def deps() -> int:
    trivy(
        "fs", "--skip-dirs", SKIP_DIRS,
        "--output", "/src/reports/trivy-deps.json", "/src",
    )  # fmt: skip
    return vulnerability_report(
        "trivy — уязвимости зависимостей приложения (requirements.txt)",
        "trivy-deps.json",
        "trivy-deps.txt",
        "deps-scan",
    )


def image(name: str | None) -> int:
    if not name:
        name = "conference-app:scan"
        print(f"Сборка образа {name} из Dockerfile")
        build = ["docker", "build", "-t", name, "."]
        if subprocess.run(build, cwd=ROOT, check=False).returncode != 0:
            sys.exit("Образ не собрался")
    CACHE.mkdir(exist_ok=True)
    tar = CACHE / "image.tar"
    save = ["docker", "save", "-o", str(tar), name]
    if subprocess.run(save, check=False).returncode != 0:
        sys.exit(f"Нет образа {name}")
    try:
        trivy(
            "image", "--input", "/src/.cache/image.tar",
            "--output", "/src/reports/trivy-image.json",
        )  # fmt: skip
    finally:
        tar.unlink(missing_ok=True)
    return vulnerability_report(
        f"trivy — уязвимости контейнерного образа {name} (пакеты ОС и Python)",
        "trivy-image.json",
        "trivy-image.txt",
        "image-scan",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("check", choices=["secrets", "deps", "image"])
    parser.add_argument("--image", help="образ для проверки (по умолчанию собрать)")
    args = parser.parse_args()
    REPORTS.mkdir(exist_ok=True)
    if args.check == "secrets":
        sys.exit(secrets())
    if args.check == "deps":
        sys.exit(deps())
    sys.exit(image(args.image))


if __name__ == "__main__":
    main()
