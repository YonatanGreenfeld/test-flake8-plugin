import ast
from pathlib import Path
from typing import Any, Dict, Generator, Optional, Set, Tuple, Type

from flake8_require_permissions.serverless_parser import get_all_http_methods, get_serverless_file_path, \
    read_serverless_yml
from flake8_require_permissions.visitor import Visitor


class Plugin:
    def __init__(self, tree: ast.AST, filename: str):
        self._tree = tree
        self._filename = filename

        self._http_methods: Optional[Set[str]] = None

    @property
    def serverless_content(self) -> Dict[str, Any]:
        serverless_file_path = get_serverless_file_path()
        if not serverless_file_path:
            raise Exception("serverless.yml not found")
        return read_serverless_yml(serverless_file_path)

    def get_http_methods(self) -> Set[str]:
        if self._http_methods is None:
            self._http_methods = get_all_http_methods(self.serverless_content)
        return self._http_methods

    def run(self) -> Generator[Tuple[int, int, str, Type[Any]], None, None]:
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

    def _get_function_name(self, func_name: str) -> Optional[str]:
        functions_base_path = self.serverless_content.get("custom", {}).get("functionsBasePath")
        serverless_file_path = get_serverless_file_path()
        if serverless_file_path is None:
            raise RuntimeError("serverless.yml not found")
        absolute_function_base_path = serverless_file_path.parent / functions_base_path
        absolute_file_name = Path(self._filename).absolute()
        try:
            relative_file_name = absolute_file_name.relative_to(absolute_function_base_path)
        except ValueError:
            return None
        return f"{relative_file_name.stem}.{func_name}"

    def _is_http_function(self, func_name: str) -> bool:
        dotted_func_name = self._get_function_name(func_name)
        if not dotted_func_name:
            return False
        return dotted_func_name in self.get_http_methods()


def foo() -> None:
    a: int = 2 + "b"
    return a
