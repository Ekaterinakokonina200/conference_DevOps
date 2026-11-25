"""Требования к инфраструктурному коду (ЛР №7), часть make infra-check.

Проверяет каталог infra/ без подключения к узлам (docs/infra.md, раздел 5):

1. Секреты: vault.yml каждого окружения зашифрован ansible-vault; vault_*
   задаются только в нём; в остальных файлах нет паролей, токенов и ключей
   в открытом виде и нет закрытых SSH-ключей.
2. Разделение параметров: имя параметра задаётся только на одном уровне —
   общем, окруженческом или узловом; у окружений одинаковый набор параметров.
3. Лишние порты: снаружи доступны только SSH и порт приложения (22, 8080),
   правила брандмауэра — только в роли firewall, порт приложения публикуется
   только на host-only адресе узла, Docker не слушает сеть.
4. Минимальные права: нет режимов 777/666, файл с секретами — 600,
   sudo без пароля — только у учётной записи Ansible.
5. Команды оболочки: у каждой задачи shell/command/raw/script есть
   комментарий «Обоснование: …» и changed_when (повторяемость результата).
6. Повторяемость: нет state: latest, обновление списка пакетов — с
   cache_valid_time, версии в requirements-infra.txt закреплены (==).

Скрипт работает в контейнере make infra-check (нужен PyYAML).
"""

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra"
ENVIRONMENTS = ("staging", "production")
ALLOWED_PORTS = {22, 8080}
SECRET_KEY = re.compile(
    r"^(.*_)?(password|passwd|secret|secret_key|token|api_key|private_key)$", re.I
)
TASK_START = re.compile(r"^(\s*)- name:", re.M)
JUSTIFICATION = "Обоснование:"
errors: list[str] = []


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def yaml_files() -> list[Path]:
    return sorted(p for p in INFRA.rglob("*.yml") if p.name not in ("vault.yml",))


def check_secrets() -> None:
    for env in ENVIRONMENTS:
        vault = INFRA / "inventories" / env / "group_vars" / "all" / "vault.yml"
        if not vault.exists():
            errors.append(f"{rel(vault)}: нет секретных параметров окружения")
        elif not vault.read_text(encoding="utf-8").startswith("$ANSIBLE_VAULT;"):
            errors.append(f"{rel(vault)}: файл не зашифрован ansible-vault")
    for path in INFRA.rglob("*"):
        if not path.is_file() or path.name == "vault.yml":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "PRIVATE KEY-----" in text:
            errors.append(f"{rel(path)}: закрытый ключ в репозитории")
    for path in yaml_files():
        if path.name == "vault.example.yml":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = re.match(r"\s*-?\s*([A-Za-z_][\w]*):\s*(.+?)\s*$", line)
            if not match or line.lstrip().startswith("#"):
                continue
            key, value = match.groups()
            value = value.strip("\"'")
            where = f"{rel(path)}:{number}"
            literal = "{{" not in value and value not in ("!", "|", ">-")
            if key.startswith("vault_"):
                errors.append(f"{where}: {key} задаётся только в vault.yml")
            elif SECRET_KEY.search(key) and key != "update_password" and literal:
                errors.append(
                    f"{where}: {key} — секрет в открытом виде (нужна ссылка на vault_…)"
                )


def check_parameter_levels() -> None:
    common = set(load(INFRA / "group_vars" / "all" / "common.yml"))
    env_keys = {}
    for env in ENVIRONMENTS:
        inventory = INFRA / "inventories" / env
        env_file = inventory / "group_vars" / "all" / "env.yml"
        keys = set(load(env_file)) if env_file.exists() else set()
        env_keys[env] = keys
        for key in sorted(keys & common):
            errors.append(f"{rel(env_file)}: {key} уже задан в общих параметрах")
        for host_file in sorted((inventory / "host_vars").glob("*.yml")):
            for key in sorted(set(load(host_file)) & (common | keys)):
                errors.append(
                    f"{rel(host_file)}: {key} уже задан на уровне общих "
                    "или окруженческих параметров"
                )
    first, second = ENVIRONMENTS
    for key in sorted(env_keys[first] ^ env_keys[second]):
        errors.append(
            f"параметр окружения {key} задан не для всех окружений ({first}, {second})"
        )


def check_ports() -> None:
    values = dict(load(INFRA / "group_vars" / "all" / "common.yml"))
    for env in ENVIRONMENTS:
        env_file = INFRA / "inventories" / env / "group_vars" / "all" / "env.yml"
        env_values = {**values, **(load(env_file) if env_file.exists() else {})}
        for key in ("ssh_port", "app_port"):
            port = env_values.get(key)
            if port not in ALLOWED_PORTS:
                errors.append(
                    f"{env}: {key}={port} — допустимы только порты "
                    f"{sorted(ALLOWED_PORTS)} (docs/infra.md)"
                )
    for path in sorted((INFRA / "roles").rglob("*.yml")):
        if "firewall" in path.parts:
            continue
        if "community.general.ufw" in path.read_text(encoding="utf-8"):
            errors.append(f"{rel(path)}: правила брандмауэра — только в роли firewall")
    for path in sorted((INFRA / "roles").rglob("*.j2")):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            published = re.match(r'\s*-\s*"([^"]+):8000"', line)
            if published and "APP_BIND" not in published.group(1):
                errors.append(f"{rel(path)}: порт приложения не на host-only адресе")
        if path.name == "daemon.json.j2" and '"hosts"' in text:
            errors.append(f"{rel(path)}: Docker не должен слушать сеть (hosts)")


def check_permissions() -> None:
    for path in sorted(INFRA.rglob("*")):
        if not path.is_file() or path.suffix not in (".yml", ".j2"):
            continue
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), 1):
            if re.search(r"mode:\s*[\"']?0?(777|666|[0-7][0-7][2367])\b", line):
                errors.append(f"{rel(path)}:{number}: права на запись для всех")
            if "NOPASSWD" in line and path.name != "sudoers-automation.j2":
                errors.append(
                    f"{rel(path)}:{number}: sudo без пароля вне учётной записи Ansible"
                )
        for block in task_blocks(text):
            if "app.env.j2" in block and not re.search(r"mode:\s*[\"']?0600", block):
                errors.append(f"{rel(path)}: файл с секретами должен иметь права 600")
            if "deploy_user" in block and re.search(r"groups:.*sudo", block):
                errors.append(f"{rel(path)}: deploy_user не должен быть в sudo")


def task_blocks(text: str) -> list[str]:
    """Задачи файла: от «- name:» (с комментариями над ней) до следующей."""
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if TASK_START.match(line)]
    blocks = []
    for index, start in enumerate(starts):
        head = start
        while head > 0 and lines[head - 1].lstrip().startswith("#"):
            head -= 1
        end = starts[index + 1] if index + 1 < len(starts) else len(lines)
        blocks.append("\n".join(lines[head:end]))
    return blocks


def check_shell_commands() -> None:
    for path in sorted(INFRA.rglob("*.yml")):
        if path.name == "vault.yml":
            continue
        for block in task_blocks(path.read_text(encoding="utf-8")):
            start = re.search(r"^(\s*)- name:\s*(.+)", block, re.M)
            indent, name = len(start.group(1)) + 2, start.group(2)
            module = re.compile(
                rf"^ {{{indent}}}(ansible\.builtin\.)?(shell|command|raw|script):", re.M
            )
            if not module.search(block):
                continue
            where = f"{rel(path)}: «{name}»"
            if JUSTIFICATION not in block:
                errors.append(f"{where} — команда без «# {JUSTIFICATION} …»")
            if "changed_when:" not in block:
                errors.append(f"{where} — команда без changed_when")
            if re.search(rf"^ {{{indent}}}(ansible\.builtin\.)?shell:", block, re.M):
                errors.append(f"{where} — shell запрещён, используйте command")


def check_repeatability() -> None:
    for path in sorted(INFRA.rglob("*.yml")):
        if path.name == "vault.yml":
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"state:\s*latest", text):
            errors.append(f"{rel(path)}: state: latest — результат зависит от даты")
        for block in task_blocks(text):
            if "update_cache: true" in block and "cache_valid_time" not in block:
                errors.append(f"{rel(path)}: update_cache без cache_valid_time")
    requirements = ROOT / "requirements-infra.txt"
    lines = requirements.read_text(encoding="utf-8").splitlines()
    for number, raw in enumerate(lines, 1):
        line = raw.split("#")[0].strip()
        if line and "==" not in line:
            errors.append(f"requirements-infra.txt:{number}: версия не зафиксирована")


def main() -> None:
    check_secrets()
    check_parameter_levels()
    check_ports()
    check_permissions()
    check_shell_commands()
    check_repeatability()
    if errors:
        print("Нарушены требования к инфраструктурному коду (docs/infra.md):")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    print("infra-policy: требования к инфраструктурному коду соблюдены")


if __name__ == "__main__":
    main()
