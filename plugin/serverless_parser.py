import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml


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
