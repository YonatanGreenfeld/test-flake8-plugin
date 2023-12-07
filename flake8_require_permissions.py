import ast
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Generator

import yaml

FULLY_QUALIFIED_NAMES = (
    "jit_utils.lambda_decorators.require_permissions",
    "jit_utils.lambda_decorators.require_permissions.require_permissions",
    "jit_utils.lambda_decorators.require_permissions.require_permissions.require_permissions",
)


class Visitor(ast.NodeVisitor):
    def __init__(self):
        self._valid_names = set()
        self._missing_decorators = set()

    @property
    def missing_decorators(self) -> set:
        return self._missing_decorators

    def visit_Import(self, node: ast.Import) -> None:
        for name in node.names:
            for FULLY_QUALIFIED_NAME in FULLY_QUALIFIED_NAMES:
                if FULLY_QUALIFIED_NAME.startswith(name.name):
                    self._valid_names.add(f"{name.asname or name.name}{FULLY_QUALIFIED_NAME[len(name.name):]}")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for name in node.names:
            full_name = f"{node.module}.{name.name}"
            for FULLY_QUALIFIED_NAME in FULLY_QUALIFIED_NAMES:
                if FULLY_QUALIFIED_NAME.startswith(full_name):
                    self._valid_names.add(f"{name.asname or name.name}{FULLY_QUALIFIED_NAME[len(full_name):]}")

    def is_valid_decorator(self, decorator: ast.expr) -> bool:
        return (
                isinstance(decorator, ast.Call) and
                self.get_full_decorator_name(decorator.func) in self._valid_names
        )

    @staticmethod
    def get_full_decorator_name(node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return Visitor.get_full_decorator_name(node.value) + '.' + node.attr
        else:
            raise TypeError("Unsupported node type: " + str(type(node)))

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


def get_all_http_methods(serverless_content: Dict[str, Any]) -> set[str]:
    http_methods = set()
    for func in serverless_content.get("functions", {}).values():
        for event in func.get("events", []):
            if event.get("http", {}).get("authorizer", {}).get("arn"):
                if handler_name := func.get("handler"):
                    http_methods.add(handler_name)
    return http_methods


class Plugin:
    def __init__(self, tree: ast.AST, filename: str):
        self._tree = tree
        self._filename = filename

        self._http_methods = None

    @property
    def serverless_content(self) -> Dict[str, Any]:
        serverless_file_path = get_serverless_file_path()
        if not serverless_file_path:
            raise Exception("serverless.yml not found")
        return read_serverless_yml(serverless_file_path)

    def get_http_methods(self) -> set[str]:
        if self._http_methods is None:
            self._http_methods = get_all_http_methods(self.serverless_content)
        return self._http_methods

    def run(self) -> Generator[tuple[int, int, str, type[Any]], None, None]:
        visitor = Visitor()
        visitor.visit(self._tree)
        for func_name, lineno, col_offset in visitor.missing_decorators:
            if self._is_http_function(func_name):
                yield (
                    lineno,
                    col_offset,
                    f"FRP001: Function: {func_name} is missing `require_permissions` decorator",
                    type(self)
                )

    def _get_function_name(self, func_name: str) -> str:
        functions_base_path = self.serverless_content.get("custom", {}).get("functionsBasePath")
        absolute_function_base_path = get_serverless_file_path().parent / functions_base_path
        absolute_file_name = Path(self._filename).absolute()
        relative_file_name = absolute_file_name.relative_to(absolute_function_base_path)
        return f"{relative_file_name.stem}.{func_name}"

    def _is_http_function(self, func_name: str):
        dotted_func_name = self._get_function_name(func_name)
        return dotted_func_name in self.get_http_methods()
