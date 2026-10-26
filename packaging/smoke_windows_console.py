"""Launch from pythonw (no parent console) and verify the native GUI creates none."""

import argparse
import ctypes
import json
import subprocess
import sys
import time
from pathlib import Path


def attached_console(process_id: int) -> bool:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.AttachConsole.argtypes = [ctypes.c_ulong]
    kernel.AttachConsole.restype = ctypes.c_int
    kernel.FreeConsole.argtypes = []
    kernel.FreeConsole.restype = ctypes.c_int
    if kernel.AttachConsole(process_id):
        kernel.FreeConsole()
        return True
    error = ctypes.get_last_error()
    if error != 6:  # ERROR_INVALID_HANDLE: the process has no console
        raise OSError(error, "could not inspect child console attachment")
    return False


def probe(executable: Path, report: Path) -> None:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.FreeConsole()
    # A console-subsystem child launched normally from pythonw must create one.
    control = subprocess.Popen(
        [
            str(Path(sys.executable).with_name("python.exe")),
            "-c",
            "import time; time.sleep(15)",
        ]
    )
    positive = False
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and control.poll() is None:
            if attached_console(control.pid):
                positive = True
                break
            time.sleep(0.1)
        if not positive:
            raise RuntimeError("positive control did not expose its console")
    finally:
        if control.poll() is None:
            control.terminate()
        control.wait(timeout=10)
    desktop = subprocess.Popen([str(executable)])
    try:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if desktop.poll() is not None:
                raise RuntimeError(
                    f"desktop exited before startup check: {desktop.returncode}"
                )
            if attached_console(desktop.pid):
                raise RuntimeError(
                    "desktop created a console when launched without a parent console"
                )
            time.sleep(0.1)
        report.write_text(
            json.dumps(
                {
                    "status": "passed",
                    "positive_control": True,
                    "console_attached": False,
                    "startup_alive": True,
                    "scope": "native desktop startup from pythonw; clean-machine GUI UAT remains separate",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    finally:
        if desktop.poll() is None:
            desktop.terminate()
        desktop.wait(timeout=10)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--executable", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    if sys.platform != "win32":
        raise RuntimeError("console smoke requires native Windows")
    args.report = args.report.resolve()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    if args.probe:
        try:
            probe(args.executable.resolve(strict=True), args.report)
        except Exception as error:
            args.report.write_text(
                json.dumps({"status": "failed", "error": str(error)}), encoding="utf-8"
            )
            raise
    else:
        from release_tools import native_executable

        executable = native_executable(args.bundle.resolve(), sys.platform)
        subprocess.run(
            [
                str(Path(sys.executable).with_name("pythonw.exe")),
                str(Path(__file__).resolve()),
                "--probe",
                "--executable",
                str(executable),
                "--report",
                str(args.report),
            ],
            check=True,
            timeout=45,
        )
        result = json.loads(args.report.read_text(encoding="utf-8"))
        if result.get("status") != "passed":
            raise RuntimeError("Windows console smoke failed")


if __name__ == "__main__":
    main()
