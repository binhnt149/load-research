"""Version checks and executable smoke tests shared by desktop release jobs."""

import argparse
import ast
import hashlib
import json
import os
import plistlib
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


def release_version(root: Path, tag: str | None = None) -> str:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    version = project["project"]["version"]
    if not isinstance(version, str) or not re.fullmatch(
        r"\d+\.\d+\.\d+(?:rc[1-9]\d*)?", version
    ):
        raise ValueError("Release version must have the form X.Y.Z or X.Y.ZrcN")
    module = ast.parse(
        (root / "src/load_research/__init__.py").read_text(encoding="utf-8")
    )
    versions = [
        ast.literal_eval(node.value)
        for node in module.body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets)
    ]
    if versions != [version]:
        raise ValueError("pyproject.toml and package __version__ must match")
    if tag is not None and tag != f"v{version}":
        raise ValueError(f"Tag must equal v{version}; received {tag!r}")
    return version


def native_executable(root: Path, system: str) -> Path:
    if system == "darwin":
        contents = root / "LoadResearch.app/Contents"
        info = plistlib.loads((contents / "Info.plist").read_bytes())
        name = info.get("CFBundleExecutable", "")
        if not isinstance(name, str) or not name or Path(name).name != name:
            raise ValueError("Invalid macOS bundle executable name")
        executable = contents / "MacOS" / name
    elif system == "win32":
        executable = root / "LoadResearch.dist/launcher.exe"
    else:
        raise ValueError(f"Unsupported native release platform: {system}")
    if not executable.is_file():
        raise ValueError(f"Native executable not found: {executable}")
    return executable


def smoke_program(command: list[str], report: Path) -> None:
    env = dict(os.environ)
    for key in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"):
        env.pop(key, None)
    env["PYTHONUTF8"] = "1"
    with tempfile.TemporaryDirectory(prefix="load-research-native-smoke-") as folder:
        work = Path(folder)
        for args in (
            ["demo", "--output", "demo", "--customers", "20"],
            [
                "run",
                "--request",
                "demo/request.json",
                "--project",
                "project",
                "--export",
                "report",
                "--charts",
                "png",
                "svg",
            ],
        ):
            completed = subprocess.run(
                [*command, *args],
                cwd=work,
                env=env,
                text=True,
                encoding="utf-8",
                capture_output=True,
                timeout=180,
            )
            if completed.returncode:
                raise RuntimeError(completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        exports = work / "report"
        checks = {
            "xlsx": (exports / "profiles.xlsx").is_file(),
            "png": bool(list(exports.rglob("*.png"))),
            "svg": bool(list(exports.rglob("*.svg"))),
        }
        if result["status"] != "completed" or not all(checks.values()):
            raise RuntimeError("Packaged demo pipeline or report export failed")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps(
            {
                "status": "passed",
                "pipeline_status": result["status"],
                **checks,
                "scope": "CLI demo and exports; clean-machine GUI UAT remains separate",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def release_assets(root: Path, version: str) -> None:
    expected = {
        f"load_research-{version}-py3-none-any.whl",
        f"LoadResearch-{version}-macos-arm64.dmg",
        f"LoadResearch-{version}-windows-x64.zip",
        "requirements.lock",
        "requirements-build.txt",
        "native-smoke-macos-arm64.json",
        "native-smoke-windows-x64.json",
    }
    files = list(root.iterdir())
    if {p.name for p in files} != expected or not all(p.is_file() for p in files):
        raise ValueError("Release assets are incomplete or contain unexpected files")
    for target in ("macos-arm64", "windows-x64"):
        report = json.loads(
            (root / f"native-smoke-{target}.json").read_text(encoding="utf-8")
        )
        if (
            report.get("status") != "passed"
            or report.get("pipeline_status") != "completed"
            or not all(report.get(k) is True for k in ("xlsx", "png", "svg"))
        ):
            raise ValueError(f"Native smoke test did not pass: {target}")
    lines = []
    for name in sorted(expected):
        with (root / name).open("rb") as stream:
            checksum = hashlib.file_digest(stream, "sha256").hexdigest()
        lines.append(f"{checksum}  {name}\n")
    (root / "SHA256SUMS").write_text("".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    version = commands.add_parser("version")
    version.add_argument("--tag")
    smoke = commands.add_parser("smoke")
    smoke.add_argument("--bundle", type=Path, required=True)
    smoke.add_argument("--report", type=Path, required=True)
    assets = commands.add_parser("assets")
    assets.add_argument("directory", type=Path)
    args = parser.parse_args()
    if args.command == "version":
        print(release_version(Path(__file__).resolve().parents[1], args.tag))
    elif args.command == "smoke":
        binary = native_executable(args.bundle.resolve(), sys.platform)
        smoke_program([str(binary)], args.report)
    else:
        release_assets(
            args.directory, release_version(Path(__file__).resolve().parents[1])
        )


if __name__ == "__main__":
    main()
