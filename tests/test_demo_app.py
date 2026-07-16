from __future__ import annotations

import importlib.util
from pathlib import Path

from codellama_algebra.demo_service import DemoGeneratedOutput


SPEC = importlib.util.spec_from_file_location("local_demo_app", Path("demo/app.py"))
APP = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(APP)


def fake(_):
    return DemoGeneratedOutput("prompt", (1,), (2,), 'print("ANSWER:", 9)', "eos", 0.01)


def test_local_only_launch_configuration():
    assert APP.LAUNCH_CONFIG["server_name"] == "127.0.0.1"
    assert APP.LAUNCH_CONFIG["share"] is False
    assert APP.LAUNCH_CONFIG["show_api"] is False
    assert APP.LAUNCH_CONFIG["mcp_server"] is False
    assert APP.LAUNCH_CONFIG["enable_monitoring"] is False


def test_ui_has_no_upload_or_arbitrary_code_surface():
    app = APP.build_app(fake)
    config = app.get_config_file()
    component_types = {component["type"] for component in config["components"]}
    assert "file" not in component_types and "uploadbutton" not in component_types
    labels = {component.get("props", {}).get("label") for component in config["components"]}
    assert "Algebra problem" in labels
    assert not any(label and "input code" in label.lower() for label in labels)
    submit_dependencies = [
        dependency
        for dependency in config["dependencies"]
        if dependency.get("targets")
        and dependency.get("backend_fn")
        and len(dependency.get("outputs", [])) == 11
    ]
    assert len(submit_dependencies) == 1
    assert submit_dependencies[0]["api_name"] is False


def test_no_persistent_logging_or_external_api_source():
    source = Path("demo/app.py").read_text()
    assert 'share": False' in source
    assert "analytics_enabled=False" in source
    assert "requests." not in source and "httpx." not in source
    assert "open(" not in source
