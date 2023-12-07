import ast

import pytest
import os
import pathlib

from plugin.plugin import Plugin


@pytest.fixture
def change_cwd_to_serverless_dir():
    """Change cwd to serverless dir"""
    cwd = os.getcwd()
    os.chdir(pathlib.Path(__file__).parent)
    yield
    os.chdir(cwd)


@pytest.mark.usefixtures("change_cwd_to_serverless_dir")
@pytest.mark.parametrize(
    "file_content",
    [pytest.param("""
from jit_utils.lambda_decorators import require_permissions
@require_permissions('required_perm')
def handler(event, context):
    pass
     """, id="from jit_utils.lambda_decorators import require_permissions"),
     pytest.param("""
from jit_utils.lambda_decorators.require_permissions import require_permissions
@require_permissions('required_perm')
def handler(event, context):
    pass
     """, id="from jit_utils.lambda_decorators.require_permissions import require_permissions"),
     pytest.param("""
from jit_utils.lambda_decorators.require_permissions.require_permissions import require_permissions
@require_permissions('required_perm')
def handler(event, context):
    pass
     """, id="from jit_utils.lambda_decorators.require_permissions.require_permissions import require_permissions"),
     pytest.param("""
import jit_utils.lambda_decorators
@jit_utils.lambda_decorators.require_permissions('required_perm')
def handler(event, context):
    pass
    """, id="import jit_utils.lambda_decorators"),
     pytest.param("""
import jit_utils.lambda_decorators.require_permissions
@jit_utils.lambda_decorators.require_permissions('required_perm')
def handler(event, context):
    pass
    """, id="import jit_utils.lambda_decorators.require_permissions"),
     ]
)
def test_plugin__http_method__validate_all_import_options(file_content: str):
    ast_tree = ast.parse(file_content)

    plugin = Plugin(ast_tree, 'src/handlers/generate_internal_api_token.py')
    errors = set(plugin.run())
    assert errors == set()


@pytest.mark.usefixtures("change_cwd_to_serverless_dir")
@pytest.mark.parametrize(
    "file_content",
    [pytest.param("""
from jit_utils.lambda_decorators import require_permissions
# @require_permissions('required_perm')
def handler(event, context):
    pass
     """, id="comment out"),
     pytest.param("""
@require_permissions('required_perm')
def handler(event, context):
    pass
     """, id="missing import"),
     pytest.param("""
def handler(event, context):
    pass
     """, id="missing decorator"),
     pytest.param("""
@warmup('required_perm')
def handler(event, context):
    pass
     """, id="wrong decorator"),
     ]
)
def test_plugin__http_method__validate_all_missing_options(file_content: str):
    ast_tree = ast.parse(file_content)

    plugin = Plugin(ast_tree, 'src/handlers/generate_internal_api_token.py')
    errors = set(plugin.run())
    assert len(errors) == 1
    assert errors.pop()[2] == "FRP001: Function: handler is missing `require_permissions` decorator"


@pytest.mark.usefixtures("change_cwd_to_serverless_dir")
def test_plugin__not_http_method():
    file_content = """
from jit_utils.lambda_decorators import require_permissions
@require_permissions('required_perm')
def handler(event, context):
    pass
     """
    ast_tree = ast.parse(file_content)

    plugin = Plugin(ast_tree, 'not_http.py')
    errors = set(plugin.run())
    assert len(errors) == 0
