"""Мутационная проверка основной логики (make mutation).

Скрипт по очереди вносит в app/services/rules.py небольшие изменения
(«мутанты»): меняет == на !=, < на <=, and на or, убирает not, подменяет
названия статусов и т. п. После каждого изменения запускаются unit-тесты.
Если тесты упали — мутант «убит»: тесты заметили изменение логики.
Если тесты прошли — мутант «выжил»: значит, такое изменение условия
(например, внесённое преподавателем на защите) осталось бы незамеченным.

Исходный файл восстанавливается после каждого мутанта, а также при
следующем запуске, если предыдущий был прерван (Ctrl+C).
"""

import ast
import copy
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "app" / "services" / "rules.py"
BACKUP_DIR = ROOT / ".mutation_backup"
BACKUP = BACKUP_DIR / "rules.py"
TEST_COMMAND = [
    sys.executable,
    "-m",
    "pytest",
    "tests/unit",
    "-x",
    "-q",
    "-p",
    "no:cacheprovider",
    "--no-header",
]

SWAP_COMPARE = {
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
    ast.Lt: ast.LtE,
    ast.LtE: ast.Lt,
    ast.Gt: ast.GtE,
    ast.GtE: ast.Gt,
    ast.In: ast.NotIn,
    ast.NotIn: ast.In,
    ast.Is: ast.IsNot,
    ast.IsNot: ast.Is,
}
SYMBOL = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.In: "in",
    ast.NotIn: "not in",
    ast.Is: "is",
    ast.IsNot: "is not",
}


def find_mutations(tree: ast.Module):
    """Список мутаций: (описание, функция, меняющая копию дерева)."""
    mutations = []
    nodes = list(ast.walk(tree))
    for index, node in enumerate(nodes):
        if isinstance(node, ast.Compare):
            for position, op in enumerate(node.ops):
                new_op = SWAP_COMPARE[type(op)]
                description = (
                    f"строка {node.lineno}: {SYMBOL[type(op)]} -> {SYMBOL[new_op]}"
                )
                mutations.append((description, index, ("compare", position, new_op)))
        elif isinstance(node, ast.BoolOp):
            new = "or" if isinstance(node.op, ast.And) else "and"
            old = "and" if new == "or" else "or"
            mutations.append(
                (f"строка {node.lineno}: {old} -> {new}", index, ("bool",))
            )
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            mutations.append((f"строка {node.lineno}: удалён not", index, ("not",)))
        elif isinstance(node, ast.Return) and not (
            node.value is None
            or (isinstance(node.value, ast.Constant) and node.value.value is None)
        ):
            mutations.append(
                (f"строка {node.lineno}: return ... -> return None", index, ("ret",))
            )
        elif (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            name = node.targets[0].id
            mutations.append(
                (f"строка {node.lineno}: изменено значение {name}", index, ("str",))
            )
    return mutations


def apply_mutation(tree: ast.Module, index: int, kind: tuple) -> ast.Module:
    mutated = copy.deepcopy(tree)
    node = list(ast.walk(mutated))[index]
    parent_map = {
        child: parent
        for parent in ast.walk(mutated)
        for child in ast.iter_child_nodes(parent)
    }
    if kind[0] == "compare":
        node.ops[kind[1]] = kind[2]()
    elif kind[0] == "bool":
        node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
    elif kind[0] == "not":
        parent = parent_map[node]
        for field, value in ast.iter_fields(parent):
            if value is node:
                setattr(parent, field, node.operand)
            elif isinstance(value, list):
                setattr(
                    parent, field, [node.operand if v is node else v for v in value]
                )
    elif kind[0] == "ret":
        node.value = ast.Constant(value=None)
    elif kind[0] == "str":
        node.value = ast.Constant(value=node.value.value + "_mutant")
    return ast.fix_missing_locations(mutated)


def restore_if_interrupted() -> None:
    if BACKUP.exists():
        shutil.copyfile(BACKUP, TARGET)
        shutil.rmtree(BACKUP_DIR, ignore_errors=True)
        print("Восстановлен rules.py после прерванного запуска.")


def run_tests() -> bool:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(
        TEST_COMMAND,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return result.returncode == 0


def main() -> None:
    restore_if_interrupted()
    if not run_tests():
        sys.exit("Unit-тесты падают и без мутаций — сначала исправьте их.")

    source = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(source)
    mutations = find_mutations(tree)

    BACKUP_DIR.mkdir(exist_ok=True)
    shutil.copyfile(TARGET, BACKUP)
    survived = []
    try:
        for number, (description, index, kind) in enumerate(mutations, 1):
            mutated = apply_mutation(tree, index, kind)
            TARGET.write_text(ast.unparse(mutated) + "\n", encoding="utf-8")
            killed = not run_tests()
            verdict = "убит" if killed else "ВЫЖИЛ"
            print(f"[{number:2}/{len(mutations)}] {description:45} {verdict}")
            if not killed:
                survived.append(description)
    finally:
        shutil.copyfile(BACKUP, TARGET)
        shutil.rmtree(BACKUP_DIR, ignore_errors=True)

    killed_count = len(mutations) - len(survived)
    print(f"\nУбито мутантов: {killed_count} из {len(mutations)}")
    if survived:
        print("Тесты не замечают изменения:")
        for description in survived:
            print(f"  - {description}")
        sys.exit(1)
    print("mutation: тесты обнаруживают каждое изменение основной логики")


if __name__ == "__main__":
    main()
