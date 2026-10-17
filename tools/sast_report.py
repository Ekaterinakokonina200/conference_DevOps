"""Статический анализ безопасности кода (make sast).

Запускает bandit для каталога app/ с настройками из pyproject.toml и выводит
полный отчёт в терминал:
  * сколько файлов и строк кода проверено;
  * сводную таблицу замечаний по уровням угрозы (важность, severity)
    и уверенности анализатора (confidence): низкая, средняя, высокая;
  * каждое замечание с файлом, строкой, правилом и уровнями;
  * обоснованные исключения (метка nosec): какое правило сработало бы, с какой
    важностью и уверенностью, и обоснование из комментария над строкой.

Политика (docs/quality-rules.md): проверку останавливает замечание ЛЮБОЙ
важности — низкой, средней или высокой. Исключение допускается только
меткой nosec на одной строке с обоснованием и записью в журнал исключений.

Тот же отчёт сохраняется в reports/bandit.txt, отчёты bandit — в
reports/bandit.html и reports/bandit.json.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
TARGET = "app"
BANDIT = [sys.executable, "-m", "bandit", "-c", "pyproject.toml", "-r", TARGET, "-q"]
# метка исключения bandit: решётка, затем слово «no» + «sec» и номера правил
NOSEC = re.compile("#" + r"\s*" + "no" + "sec" + r"\b\s*([A-Z0-9, .]*)")
LEVELS = ("HIGH", "MEDIUM", "LOW")
NAMES = {"HIGH": "высокая", "MEDIUM": "средняя", "LOW": "низкая", "UNDEFINED": "—"}


def run_bandit(fmt: str, output: Path, *extra: str) -> int:
    cmd = [*BANDIT, *extra, "-f", fmt, "-o", str(output)]
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


def load(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"bandit не запустился: отчёт {path.relative_to(ROOT)} не создан")
    return json.loads(path.read_text(encoding="utf-8"))


def level(value: str) -> str:
    return NAMES.get(value, value)


def matrix(issues: list[dict]) -> list[str]:
    """Таблица «важность × уверенность» с итогами."""
    rows = ["    важность \\ уверенность   высокая  средняя  низкая   всего"]
    for sev in LEVELS:
        counts = [
            sum(
                1
                for i in issues
                if i["issue_severity"] == sev and i["issue_confidence"] == conf
            )
            for conf in LEVELS
        ]
        rows.append(
            f"    {level(sev):<24}"
            + "".join(f"{c:>9}" for c in counts)
            + f"{sum(counts):>8}"
        )
    totals = [sum(1 for i in issues if i["issue_confidence"] == c) for c in LEVELS]
    rows.append(
        f"    {'всего':<24}" + "".join(f"{c:>9}" for c in totals) + f"{len(issues):>8}"
    )
    return rows


def justification(filename: str, number: int) -> str:
    """Обоснование — комментарий на строке над меткой nosec."""
    lines = (ROOT / filename).read_text(encoding="utf-8").splitlines()
    above = lines[number - 2].strip() if number > 1 else ""
    reason = above.lstrip("# ").strip() if above.startswith("#") else ""
    return re.sub(r"^Обоснование:\s*", "", reason)


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    main_json = REPORTS / "bandit.json"
    code = run_bandit("json", main_json)
    run_bandit("html", REPORTS / "bandit.html")
    data = load(main_json)

    # Тот же анализ без учёта меток nosec — чтобы показать, какие замечания
    # подавлены исключениями и с какими уровнями угрозы.
    raw_json = REPORTS / "bandit-ignore-nosec.json"
    run_bandit("json", raw_json, "--ignore-nosec")
    raw = load(raw_json)

    totals = data["metrics"]["_totals"]
    skipped = totals.get("nosec", 0) + totals.get("skipped_tests", 0)
    files = [name for name in data["metrics"] if name != "_totals"]
    issues = data["results"]
    active = {(i["filename"], i["line_number"], i["test_id"]) for i in issues}
    suppressed = [
        i
        for i in raw["results"]
        if (i["filename"], i["line_number"], i["test_id"]) not in active
    ]

    out = [
        f"bandit — статический анализ безопасности (SAST), каталог {TARGET}/",
        f"  проверено файлов: {len(files)}, строк кода: {totals['loc']}, "
        f"подавлено меткой nosec: {skipped}",
        "  политика: проверку останавливает замечание любой важности "
        "(высокой, средней, низкой)",
        "",
        f"  Действующие замечания: {len(issues)}",
        *matrix(issues),
    ]
    for item in issues:
        out.append(
            f"    {item['filename']}:{item['line_number']}  {item['test_id']} "
            f"{item['test_name']}  важность: {level(item['issue_severity'])}, "
            f"уверенность: {level(item['issue_confidence'])}"
        )
        out.append(f"      {item['issue_text']}")
        out.append(f"      подробнее: {item['more_info']}")

    out += ["", f"  Подавлены исключениями (nosec): {len(suppressed)}"]
    if suppressed:
        out += matrix(suppressed)
    for item in suppressed:
        reason = justification(item["filename"], item["line_number"])
        out.append(
            f"    {item['filename']}:{item['line_number']}  {item['test_id']} "
            f"{item['test_name']}  важность: {level(item['issue_severity'])}, "
            f"уверенность: {level(item['issue_confidence'])}"
        )
        out.append(f"      {item['issue_text']}")
        out.append(
            f"      обоснование: {reason or 'НЕТ — запрещено правилами качества'}"
        )

    unjustified = [
        i for i in suppressed if not justification(i["filename"], i["line_number"])
    ]
    if issues:
        verdict = f"bandit: замечаний {len(issues)} — исправить код"
    elif unjustified:
        verdict = f"bandit: исключений без обоснования {len(unjustified)}"
    else:
        verdict = "bandit: замечаний нет"
    out += [
        "",
        "  отчёты: reports/bandit.txt, reports/bandit.html, reports/bandit.json",
        "",
        verdict,
    ]

    text = "\n".join(out)
    (REPORTS / "bandit.txt").write_text(text + "\n", encoding="utf-8")
    print(text)
    if issues or unjustified or code not in (0, 1):
        sys.exit(1)


if __name__ == "__main__":
    main()
