import hashlib
import importlib.util
import json
import plistlib
import sys
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "release_tools", Path(__file__).parents[2] / "packaging/release_tools.py"
)
assert spec is not None and spec.loader is not None
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


def metadata(tmp_path, package_version="0.1.0", project_version="0.1.0"):
    (tmp_path / "src/load_research").mkdir(parents=True)
    (tmp_path / "src/load_research/__init__.py").write_text(
        f'__version__ = "{package_version}"\n'
    )
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nversion = "{project_version}"\n'
    )
    return tmp_path


def test_release_version_agrees_with_both_metadata_sources_and_tag(tmp_path):
    root = metadata(tmp_path)
    assert release.release_version(root, "v0.1.0") == "0.1.0"
    assert release.release_version(root) == "0.1.0"


def test_release_candidate_version_agrees_with_metadata_and_tag(tmp_path):
    root = metadata(tmp_path, package_version="0.1.4rc1", project_version="0.1.4rc1")
    assert release.release_version(root, "v0.1.4rc1") == "0.1.4rc1"


@pytest.mark.parametrize("tag", ["v0.1.1", "0.1.0", "v0.1.0;echo BAD", "v../x"])
def test_release_refuses_mismatched_or_unsafe_tags(tmp_path, tag):
    with pytest.raises(ValueError):
        release.release_version(metadata(tmp_path), tag)


def test_release_refuses_inconsistent_package_version(tmp_path):
    with pytest.raises(ValueError):
        release.release_version(metadata(tmp_path, package_version="0.2.0"))


def test_macos_entrypoint_comes_from_bundle_metadata(tmp_path):
    contents = tmp_path / "LoadResearch.app/Contents"
    (contents / "MacOS").mkdir(parents=True)
    (contents / "Info.plist").write_bytes(
        plistlib.dumps({"CFBundleExecutable": "launcher"})
    )
    executable = contents / "MacOS/launcher"
    executable.touch()
    assert release.native_executable(tmp_path, "darwin") == executable


@pytest.mark.parametrize("name", ["../outside", "/outside", "missing"])
def test_macos_entrypoint_rejects_escape_and_missing_binary(tmp_path, name):
    contents = tmp_path / "LoadResearch.app/Contents"
    contents.mkdir(parents=True)
    (contents / "Info.plist").write_bytes(plistlib.dumps({"CFBundleExecutable": name}))
    with pytest.raises(ValueError):
        release.native_executable(tmp_path, "darwin")


def test_windows_entrypoint_requires_the_standalone_binary(tmp_path):
    with pytest.raises(ValueError):
        release.native_executable(tmp_path, "win32")
    executable = tmp_path / "LoadResearch.dist/launcher.exe"
    executable.parent.mkdir()
    executable.touch()
    assert release.native_executable(tmp_path, "win32") == executable


def test_release_smoke_runs_a_real_program_outside_the_checkout(tmp_path):
    report = tmp_path / "smoke.json"
    release.smoke_program([sys.executable, "-m", "load_research"], report)
    result = json.loads(report.read_text())
    assert result["status"] == "passed"
    assert result["pipeline_status"] == "completed"
    assert result["xlsx"] and result["png"] and result["svg"]
    assert str(tmp_path) not in report.read_text()


def test_failing_program_cannot_publish_a_passing_smoke_report(tmp_path):
    report = tmp_path / "smoke.json"
    with pytest.raises(RuntimeError):
        release.smoke_program([sys.executable, "-c", "raise SystemExit(7)"], report)
    assert not report.exists()


def assets(tmp_path):
    for name in (
        "load_research-0.1.0-py3-none-any.whl",
        "LoadResearch-0.1.0-macos-arm64.dmg",
        "LoadResearch-0.1.0-windows-x64.zip",
        "requirements.lock",
        "requirements-build.txt",
    ):
        (tmp_path / name).write_bytes(b"synthetic release asset")
    for target in ("macos-arm64", "windows-x64"):
        (tmp_path / f"native-smoke-{target}.json").write_text(
            json.dumps(
                {
                    "status": "passed",
                    "pipeline_status": "completed",
                    "xlsx": True,
                    "png": True,
                    "svg": True,
                }
            )
        )
    return tmp_path


def test_checksum_manifest_covers_every_release_asset(tmp_path):
    release.release_assets(assets(tmp_path), "0.1.0")
    lines = (tmp_path / "SHA256SUMS").read_text().splitlines()
    assert len(lines) == 7
    for line in lines:
        checksum, name = line.split()
        assert checksum == hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()


@pytest.mark.parametrize("problem", ["missing-dmg", "extra-file", "failed-smoke"])
def test_incomplete_or_failed_assets_cannot_get_a_checksum_manifest(tmp_path, problem):
    root = assets(tmp_path)
    if problem == "missing-dmg":
        (root / "LoadResearch-0.1.0-macos-arm64.dmg").unlink()
    elif problem == "extra-file":
        (root / "unintended-data.csv").touch()
    else:
        (root / "native-smoke-windows-x64.json").write_text('{"status":"failed"}')
    with pytest.raises(ValueError):
        release.release_assets(root, "0.1.0")
    assert not (root / "SHA256SUMS").exists()
