import ast
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Generator

import yaml

FULLY_QUALIFIED_NAME = "jit_utils.lambda_decorators.require_permissions"


class Visitor(ast.NodeVisitor):
    def __init__(self):
        self._valid_names = set()
        self._missing_decorators = set()

    @property
    def missing_decorators(self) -> set:
        return self._missing_decorators

    def visit_Import(self, node: ast.Import) -> None:
        for name in node.names:
            if FULLY_QUALIFIED_NAME.startswith(name.name):
                self._valid_names.add(f"{name.asname or name.name}{FULLY_QUALIFIED_NAME[len(name.name):]}")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for name in node.names:
            full_name = f"{node.module}.{name.name}"
            if FULLY_QUALIFIED_NAME.startswith(full_name):
                self._valid_names.add(f"{name.asname or name.name}{FULLY_QUALIFIED_NAME[len(full_name):]}")

    def is_valid_decorator(self, decorator: ast.expr) -> bool:
        return (
                isinstance(decorator, ast.Call) and
                isinstance(decorator.func, ast.Name) and
                decorator.func.id in self._valid_names
        )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if not any(self.is_valid_decorator(decorator) for decorator in node.decorator_list):
            self._missing_decorators.add((node.name, node.lineno, node.col_offset))
        self.generic_visit(node)


@lru_cache()
def read_serverless_yml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text())


@lru_cache()
def get_serverless_file_path() -> Path:
    current_dir = Path(os.getcwd())
    while current_dir != current_dir.parent:
        if (current_dir / "serverless.yml").exists():
            return current_dir / "serverless.yml"
        if (current_dir / "serverless.yaml").exists():
            return current_dir / "serverless.yaml"
        current_dir = current_dir.parent


class Plugin:
    def __init__(self, tree: ast.AST):
        self._tree = tree

    @property
    def serverless_content(self) -> Dict[str, Any]:
        serverless_file_path = get_serverless_file_path()
        if not serverless_file_path:
            raise Exception("serverless.yml not found")
        return read_serverless_yml(serverless_file_path)

    def run(self) -> Generator[tuple[int, int, str, type[Any]], None, None]:
        visitor = Visitor()
        visitor.visit(self._tree)
        for func_name, lineno, col_offset in visitor.missing_decorators:
            yield (
                lineno,
                col_offset,
                f"FRP001: Function: {func_name} is missing `require_permissions` decorator",
                type(self)
            )
