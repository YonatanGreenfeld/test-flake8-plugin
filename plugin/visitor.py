import ast

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
