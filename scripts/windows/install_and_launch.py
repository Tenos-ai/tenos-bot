"""Automated installer and launcher for the Tenos.ai Material configurator.

The script performs the following steps when invoked from ``TENOSAI-BOT.bat``
(or manually with ``python scripts/windows/install_and_launch.py``):

* Creates (or re-uses) a dedicated virtual environment under ``.venv``.
* Installs the required Python dependencies for both the Discord bot and the
  Material GUI, including Windows specific wheels such as ``pywin32`` and
  ``PyInstaller``.
* Invokes :mod:`tools.build_configurator` to freeze the Material GUI into a
  distributable Windows bundle that ships the Python runtime DLL.
* Creates a ``.lnk`` shortcut in the repository root pointing at the freshly
  built executable for quick access outside the installer flow.
* Launches the Material GUI once provisioning completes so first-time users
  can immediately start configuring their environment.

The script is intentionally written with only the Python standard library so
it can run before any third-party packages are installed.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VENV = PROJECT_ROOT / ".venv"
TOOLS_DIR = PROJECT_ROOT / "tools"
REQUIREMENTS_DIR = PROJECT_ROOT / "requirements"
DEFAULT_APP_NAME = "TenosAIConfigurator"


class InstallerError(RuntimeError):
    """Raised when one of the provisioning steps fails."""


def _log(message: str) -> None:
    print(f"[installer] {message}")


def _run(command: Iterable[str], *, env: dict[str, str] | None = None) -> None:
    command = list(map(str, command))
    _log("running: " + " ".join(command))
    result = subprocess.run(command, cwd=PROJECT_ROOT, env=env, check=False)
    if result.returncode != 0:
        raise InstallerError(
            f"command '{' '.join(command)}' exited with status {result.returncode}"
        )


def _ensure_python_version() -> None:
    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10 or newer is required to install Tenos.ai bot tooling.")


def _ensure_venv(venv_path: Path) -> Path:
    if not venv_path.exists():
        _log(f"creating virtual environment at {venv_path}")
        _run([sys.executable, "-m", "venv", str(venv_path)])
    else:
        _log(f"reusing existing virtual environment at {venv_path}")

    if os.name == "nt":
        python_path = venv_path / "Scripts" / "python.exe"
    else:
        python_path = venv_path / "bin" / "python"

    if not python_path.exists():
        raise InstallerError(f"virtual environment is missing a Python interpreter at {python_path}")

    return python_path


def _pip_install(python_exe: Path, *packages: str) -> None:
    if not packages:
        return
    _run([python_exe, "-m", "pip", "install", "--upgrade", *packages])


def _install_requirements(python_exe: Path) -> None:
    base_file = REQUIREMENTS_DIR / "base.txt"
    windows_file = REQUIREMENTS_DIR / "windows.txt"

    if not base_file.exists():
        raise InstallerError(f"missing dependency manifest: {base_file}")

    _pip_install(python_exe, "pip", "wheel", "setuptools")
    _run([python_exe, "-m", "pip", "install", "--upgrade", "-r", str(base_file)])

    if os.name == "nt" and windows_file.exists():
        _run([python_exe, "-m", "pip", "install", "--upgrade", "-r", str(windows_file)])


def _build_executable(python_exe: Path, app_name: str, clean: bool, onefile: bool, zip_bundle: bool) -> Path:
    build_script = TOOLS_DIR / "build_configurator.py"
    if not build_script.exists():
        raise InstallerError(f"build script not found: {build_script}")

    command: list[str] = [str(python_exe), str(build_script), "--app-name", app_name]
    if clean:
        command.append("--clean")
    if onefile:
        command.append("--onefile")
    if zip_bundle and not onefile:
        command.append("--zip")

    _run(command)

    dist_dir = PROJECT_ROOT / "dist" / app_name
    exe_path = dist_dir / f"{app_name}.exe"
    if not exe_path.exists():
        raise InstallerError(f"expected executable not found at {exe_path}")

    return exe_path


def _create_shortcut(exe_path: Path, shortcut_path: Path) -> bool:
    if os.name != "nt":
        _log("shortcut creation skipped (not running on Windows)")
        return False

    try:
        import pythoncom  # type: ignore  # noqa: F401 - imported for side effects
        from win32com.client import Dispatch
    except ImportError:
        _log("pywin32 is not installed; skipping shortcut creation")
        return False

    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(shortcut_path))
    shortcut.Targetpath = str(exe_path)
    shortcut.WorkingDirectory = str(exe_path.parent)
    shortcut.IconLocation = str(exe_path)
    shortcut.save()
    _log(f"created shortcut at {shortcut_path}")
    return True


def _launch_material_gui(exe_path: Path, python_exe: Path, mode: str) -> None:
    if mode == "skip":
        _log("launch step skipped by user request")
        return

    if mode == "exe" and exe_path.exists():
        _log(f"launching Material GUI executable {exe_path}")
        subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent))
        return

    _log("falling back to launching the Material GUI from source")
    subprocess.Popen([str(python_exe), "-m", "material_gui.app"], cwd=str(PROJECT_ROOT))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Provision and launch the Tenos.ai Material configurator")
    parser.add_argument("--venv", default=str(DEFAULT_VENV), help="Path to the virtual environment (default: %(default)s)")
    parser.add_argument("--app-name", default=DEFAULT_APP_NAME, help="Name of the packaged executable")
    parser.add_argument("--skip-build", action="store_true", help="Skip rebuilding the executable if it already exists")
    parser.add_argument("--no-shortcut", action="store_true", help="Do not create a desktop shortcut in the project root")
    parser.add_argument("--no-clean", action="store_true", help="Do not purge previous PyInstaller output before building")
    parser.add_argument("--onefile", action="store_true", help="Generate a single-file executable instead of a folder bundle")
    parser.add_argument("--no-zip", action="store_true", help="Do not emit an additional portable .zip archive")
    parser.add_argument(
        "--launch-mode",
        choices=["exe", "source", "skip"],
        default="exe",
        help="How to start the configurator after provisioning (default: %(default)s)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _ensure_python_version()
    args = parse_args(argv)

    venv_path = Path(args.venv).resolve()
    try:
        venv_python = _ensure_venv(venv_path)
        _install_requirements(venv_python)

        dist_dir = PROJECT_ROOT / "dist" / args.app_name
        exe_path = dist_dir / f"{args.app_name}.exe"

        if args.skip_build and exe_path.exists():
            _log(f"using existing executable at {exe_path}")
        else:
            exe_path = _build_executable(
                venv_python,
                args.app_name,
                clean=not args.no_clean,
                onefile=args.onefile,
                zip_bundle=not args.no_zip,
            )

        if not args.no_shortcut:
            shortcut_path = PROJECT_ROOT / f"{args.app_name}.lnk"
            _create_shortcut(exe_path, shortcut_path)

        launch_mode = args.launch_mode
        if launch_mode == "source":
            _launch_material_gui(exe_path, venv_python, mode="source")
        else:
            _launch_material_gui(exe_path, venv_python, mode="exe" if launch_mode == "exe" else "skip")

        _log("installation finished successfully")
        return 0
    except InstallerError as exc:
        _log(f"error: {exc}")
        return 1


if __name__ == "__main__":  # pragma: no cover - entry point
    raise SystemExit(main())
