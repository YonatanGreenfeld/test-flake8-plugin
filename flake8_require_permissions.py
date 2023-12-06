import ast
from typing import Any, Generator


class Plugin:
    def __init__(self, tree: ast.AST):
        self._tree = tree

    def run(self) -> Generator[tuple[int, int, str, type[Any]], None, None]:
        yield 2, 3, "FRP001: Path: flake8_require_permissions.py", type(self)
