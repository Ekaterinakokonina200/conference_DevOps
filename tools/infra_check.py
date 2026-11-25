"""Проверка инфраструктурного кода (ЛР №7): make infra-check.

Одна и та же проверка локально (Docker Desktop) и в pipeline Infrastructure:
инструменты работают в контейнере из docker/ansible/Dockerfile с версиями из
requirements-infra.txt, к узлам ничего не подключается.

  1. yamllint — оформление YAML (infra/.yamllint);
  2. ansible-lint — профиль production (infra/.ansible-lint);
  3. ansible-playbook --syntax-check — bootstrap, site, verify для staging и
     production;
  4. tools/infra_policy.py — требования к инфраструктурному коду
     (секреты, параметры, порты, права, команды, повторяемость).
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "conference-infra:check"
PLAYBOOKS = ("bootstrap.yml", "site.yml", "verify.yml")
ENVIRONMENTS = ("staging", "production")

# Плейбуки появляются по этапам работы: проверяются те, что уже есть
EXISTING = [name for name in PLAYBOOKS if (ROOT / "infra" / name).exists()]
STEPS = [
    ("yamllint", "cd infra && yamllint -s -c .yamllint ."),
    ("ansible-lint", "cd infra && ansible-lint -q"),
    *[
        (
            f"syntax-check {env}",
            f"cd infra && ansible-playbook -i inventories/{env} --syntax-check "
            + " ".join(EXISTING),
        )
        for env in ENVIRONMENTS
    ],
    ("infra-policy", "python tools/infra_policy.py"),
]


def docker(*args: str, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], check=False, **kwargs)


def build_image() -> None:
    """Образ с инструментами: контекст — только Dockerfile и requirements."""
    with tempfile.TemporaryDirectory() as context:
        shutil.copy(ROOT / "docker" / "ansible" / "Dockerfile", context)
        shutil.copy(ROOT / "requirements-infra.txt", context)
        print(f"Образ инструментов {IMAGE} (docker/ansible/Dockerfile)", flush=True)
        result = docker("build", "-q", "-t", IMAGE, context, capture_output=True)
        if result.returncode != 0:
            sys.exit(result.stderr.decode(errors="replace") + "\nОбраз не собрался")


def main() -> None:
    if not shutil.which("docker"):
        sys.exit("Не найден docker. Запустите Docker Desktop или Docker (CI).")
    build_image()
    run = ["run", "--rm", "-v", f"{ROOT}:/src", "-w", "/src"]
    run += ["-e", "ANSIBLE_CONFIG=/src/infra/ansible.cfg"]
    if hasattr(os, "getuid"):  # Linux, CI
        run += ["--user", f"{os.getuid()}:{os.getgid()}"]
    failed = []
    for number, (title, command) in enumerate(STEPS, 1):
        print(f"\n[{number}/{len(STEPS)}] {title}", flush=True)
        code = docker(*run, IMAGE, "sh", "-c", command).returncode
        if code == 0:
            print("  ok", flush=True)
        else:
            failed.append(title)
    if failed:
        sys.exit(f"\ninfra-check: не пройдено: {', '.join(failed)}")
    print("\ninfra-check: инфраструктурный код проверен")


if __name__ == "__main__":
    main()
