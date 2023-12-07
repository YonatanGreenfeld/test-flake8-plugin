from pathlib import Path

import pytest
import yaml

from plugin.serverless_parser import get_all_http_methods


@pytest.fixture()
def serverless_content():
    serverless_file = Path(__file__).parent / "serverless.yml"
    return yaml.safe_load(serverless_file.read_text())


def test_get_all_http_methods(serverless_content):
    http_methods = get_all_http_methods(serverless_content)
    assert http_methods == {
        'authenticate_api_token.handler',
        'generate_internal_api_token.handler',
        'get_registry_login_password.handler'
    }
