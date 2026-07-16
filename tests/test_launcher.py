from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import tempfile
import time



ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "run-algalpaca"


def _write_executable(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def fake_project(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    project = tmp_path / "project"
    project.mkdir()
    shutil.copy2(LAUNCHER, project / "run-algalpaca")
    adapter = tmp_path / "adapter"
    adapter.mkdir()
    frontend = project / "frontend"
    (frontend / "src").mkdir(parents=True)
    (frontend / "dist").mkdir()
    (frontend / "node_modules").mkdir()
    for name in (
        "package.json",
        "package-lock.json",
        "tsconfig.json",
        "tsconfig.app.json",
        "tsconfig.node.json",
        "vite.config.ts",
    ):
        (frontend / name).write_text("{}\n", encoding="utf-8")
    (frontend / "src/main.tsx").write_text("// source\n", encoding="utf-8")
    time.sleep(0.01)
    (frontend / "dist/index.html").write_text("built\n", encoding="utf-8")
    time.sleep(0.01)
    (frontend / "node_modules/.package-lock.json").write_text("{}\n", encoding="utf-8")
    bin_dir = Path(tempfile.mkdtemp(prefix="algalpaca-launcher-bin-", dir="/tmp"))
    capture = tmp_path / "capture"
    _write_executable(
        project / ".venv/bin/python",
        "#!/usr/bin/env bash\n"
        "if [[ ${1:-} == -c ]]; then exit 0; fi\n"
        "printf '%s\\n' \"${CODELLAMA_ALGEBRA_ADAPTER_PATH:-}\" > \"$CAPTURE/adapter\"\n"
        "printf '%s\\n' \"$*\" > \"$CAPTURE/python-args\"\n"
        "trap 'exit 130' INT TERM\n"
        "while :; do sleep 0.05; done\n",
    )
    _write_executable(bin_dir / "node", "#!/usr/bin/env bash\nexit 0\n")
    _write_executable(
        bin_dir / "npm",
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$*\" >> \"$CAPTURE/npm-calls\"\n"
        "if [[ ${1:-} == run && ${2:-} == build ]]; then mkdir -p dist; printf built > dist/index.html; fi\n"
        "exit 0\n",
    )
    capture.mkdir()
    environment = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "CAPTURE": str(capture),
        "CODELLAMA_ALGEBRA_ADAPTER_PATH": str(adapter),
    }
    return project, environment


def test_launcher_exists_is_executable_and_has_valid_bash_syntax():
    assert LAUNCHER.is_file()
    assert os.access(LAUNCHER, os.X_OK)
    subprocess.run(["bash", "-n", str(LAUNCHER)], check=True)


def test_check_resolves_own_root_and_does_not_start_server(tmp_path: Path):
    project, environment = fake_project(tmp_path)
    completed = subprocess.run(
        [str(project / "run-algalpaca"), "--check"],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "check passed" in completed.stdout
    assert not (Path(environment["CAPTURE"]) / "python-args").exists()


def test_unknown_argument_fails_with_usage(tmp_path: Path):
    project, environment = fake_project(tmp_path)
    completed = subprocess.run(
        [str(project / "run-algalpaca"), "--unknown"],
        env=environment,
        text=True,
        capture_output=True,
    )
    assert completed.returncode == 2
    assert "Usage:" in completed.stderr


def test_environment_adapter_takes_precedence_over_local_file(tmp_path: Path):
    project, environment = fake_project(tmp_path)
    (project / ".algalpaca-adapter-path").write_text("/missing/path\n", encoding="utf-8")
    process = subprocess.Popen([str(project / "run-algalpaca")], env=environment)
    try:
        capture = Path(environment["CAPTURE"]) / "adapter"
        for _ in range(100):
            if capture.exists():
                break
            time.sleep(0.02)
        assert capture.read_text(encoding="utf-8").strip() == environment[
            "CODELLAMA_ALGEBRA_ADAPTER_PATH"
        ]
    finally:
        process.send_signal(signal.SIGINT)
        process.wait(timeout=3)


def test_local_adapter_file_and_multiline_rejection(tmp_path: Path):
    project, environment = fake_project(tmp_path)
    adapter = environment.pop("CODELLAMA_ALGEBRA_ADAPTER_PATH")
    (project / ".algalpaca-adapter-path").write_text(f"  {adapter}  \n", encoding="utf-8")
    assert subprocess.run([str(project / "run-algalpaca"), "--check"], env=environment).returncode == 0
    (project / ".algalpaca-adapter-path").write_text(f"{adapter}\n{adapter}\n", encoding="utf-8")
    failed = subprocess.run(
        [str(project / "run-algalpaca"), "--check"], env=environment, text=True, capture_output=True
    )
    assert failed.returncode == 1
    assert "exactly one line" in failed.stderr


def test_no_unnecessary_install_or_build_and_rebuild_forces_build(tmp_path: Path):
    project, environment = fake_project(tmp_path)
    subprocess.run([str(project / "run-algalpaca"), "--check"], env=environment, check=True)
    assert not (Path(environment["CAPTURE"]) / "npm-calls").exists()
    started = subprocess.Popen([str(project / "run-algalpaca"), "--rebuild"], env=environment)
    try:
        calls = Path(environment["CAPTURE"]) / "npm-calls"
        for _ in range(100):
            if calls.exists() and "run build" in calls.read_text(encoding="utf-8"):
                break
            time.sleep(0.02)
        text = calls.read_text(encoding="utf-8")
        assert "run build" in text
        assert "ci" not in text.splitlines()
    finally:
        server = Path(environment["CAPTURE"]) / "python-args"
        for _ in range(100):
            if server.exists():
                break
            time.sleep(0.02)
        started.send_signal(signal.SIGINT)
        started.wait(timeout=3)


def test_missing_build_rejects_windows_node_or_npm(tmp_path: Path):
    project, environment = fake_project(tmp_path)
    (project / "frontend/dist/index.html").unlink()
    environment["BASH_FUNC_command%%"] = (
        "() { if [[ $1 == -v && $2 == node ]]; then printf '%s\n' '/mnt/c/node.exe'; "
        "elif [[ $1 == -v && $2 == npm ]]; then printf '%s\n' '/mnt/c/npm'; "
        "else builtin command \"\"; fi; }"
    )
    failed = subprocess.run(
        [str(project / "run-algalpaca"), "--check"], env=environment, text=True, capture_output=True
    )
    assert failed.returncode == 1
    assert "Windows node or npm" in failed.stderr


def test_normal_launch_uses_local_web_module_and_ctrl_c_is_forwarded(tmp_path: Path):
    project, environment = fake_project(tmp_path)
    process = subprocess.Popen(
        [str(project / "run-algalpaca")], env=environment, text=True, stdout=subprocess.PIPE
    )
    try:
        capture = Path(environment["CAPTURE"]) / "python-args"
        for _ in range(100):
            if capture.exists():
                break
            time.sleep(0.02)
        assert capture.read_text(encoding="utf-8").strip() == "-m codellama_algebra.web_api"
        assert "http://127.0.0.1:8000" in process.stdout.readline()
    finally:
        process.send_signal(signal.SIGINT)
        assert process.wait(timeout=3) == 130


def test_example_is_generic_and_private_path_file_is_ignored():
    example = (ROOT / ".algalpaca-adapter-path.example").read_text(encoding="utf-8")
    assert example == "/path/to/local/adapter\n"
    assert "/home/" not in example
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", ".algalpaca-adapter-path"], cwd=ROOT
    )
    assert ignored.returncode == 0
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", ".algalpaca-adapter-path"],
        cwd=ROOT,
        capture_output=True,
    )
    assert tracked.returncode != 0
