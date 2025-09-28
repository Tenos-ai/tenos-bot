"""PyInstaller build helper for the Tenos.ai configurator GUI.

This module provides a small command line utility that assembles the
Material configurator into a portable Windows bundle.  The script
handles repetitive PyInstaller arguments (icon wiring, resource data,
and hidden imports) so contributors only have to install PyInstaller
and run a single command.

Usage (from the repository root)::

    python packaging/build_configurator.py

The default invocation creates a ``dist/TenosAIConfigurator`` directory
containing ``TenosAIConfigurator.exe`` alongside the required assets.
Pass ``--zip`` to additionally emit a portable ``.zip`` that can be
shared with end users.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = PROJECT_ROOT / "config_editor_main.py"
ICON_PATH = PROJECT_ROOT / "tenos-ai_icon.ico"
DEFAULT_APP_NAME = "TenosAIConfigurator"
DIST_ROOT = PROJECT_ROOT / "dist"
BUILD_ROOT = PROJECT_ROOT / "build"

# Data files that the configurator expects to live next to the executable.
# They are copied verbatim into the PyInstaller bundle.
DATA_FILES: tuple[tuple[Path, str], ...] = (
    (PROJECT_ROOT / "config.json", "."),
    (PROJECT_ROOT / "settings.json", "."),
    (PROJECT_ROOT / "styles.json", "."),
    (PROJECT_ROOT / "styles_config.json", "."),
    (PROJECT_ROOT / "llm_prompts.json", "."),
    (PROJECT_ROOT / "llm_models.json", "."),
    (PROJECT_ROOT / "modelnodes.json", "."),
    (PROJECT_ROOT / "tenosai_theme.json", "."),
    (PROJECT_ROOT / "tenos-ai_icon.png", "."),
)

# PySide6 occasionally requires explicit hidden-import hints for widgets
# that are imported lazily by Qt.  Listing them here avoids runtime
# ``ModuleNotFoundError`` exceptions in frozen builds.
HIDDEN_IMPORTS = (
    "PySide6.QtGui",
    "PySide6.QtCore",
    "PySide6.QtWidgets",
)


class BuildError(RuntimeError):
    """Raised when PyInstaller exits with a non-zero status."""


def _normalize_add_data_argument(src: Path, dest: str) -> str:
    """Return a properly formatted ``--add-data`` argument."""

    separator = ";" if os.name == "nt" else ":"
    return f"{src}{separator}{dest}"


def _ensure_pyinstaller() -> None:
    """Abort early if PyInstaller is not importable."""

    try:
        import PyInstaller  # noqa: F401  - only verifying availability
    except ModuleNotFoundError as exc:  # pragma: no cover - defensive branch
        message = (
            "PyInstaller is required to build the configurator bundle.\n"
            "Install it with 'pip install pyinstaller' and re-run this command."
        )
        raise SystemExit(message) from exc


def _build_pyinstaller_command(args: argparse.Namespace) -> list[str]:
    """Construct the PyInstaller command line arguments."""

    command = [sys.executable, "-m", "PyInstaller", "--noconfirm"]

    if args.clean:
        command.append("--clean")

    command.extend(("--name", args.app_name))
    command.append("--windowed")

    if ICON_PATH.exists():
        command.extend(("--icon", str(ICON_PATH)))

    # Copy user-facing resources such as configuration templates alongside
    # the executable so fresh installs have sensible defaults.
    for src, dest in DATA_FILES:
        if not src.exists():
            # Missing optional resource – skip it silently but surface a
            # helpful note so maintainers notice.
            print(f"[build] warning: data file '{src.name}' not found, skipping")
            continue
        command.extend(("--add-data", _normalize_add_data_argument(src, dest)))

    for hidden in HIDDEN_IMPORTS:
        command.extend(("--hidden-import", hidden))

    # ``pythonXY.dll`` is not always bundled automatically when PyInstaller runs
    # from a virtual environment on Windows.  If it is missing, the frozen
    # executable immediately aborts with ``Failed to load Python DLL`` which is
    # the error users have reported.  Detect the base interpreter's DLL and ship
    # it explicitly so the bundle is self-contained.
    if os.name == "nt":  # pragma: win32-cover
        python_dll = Path(sys.base_prefix) / f"python{sys.version_info.major}{sys.version_info.minor}.dll"
        if python_dll.exists():
            command.extend(("--add-binary", _normalize_add_data_argument(python_dll, ".")))
        else:  # pragma: no cover - depends on external interpreter layout
            print(
                "[build] warning: could not locate 'python*.dll' in base interpreter; "
                "the resulting executable may fail to start"
            )

    if args.onefile:
        command.append("--onefile")

    command.append(str(ENTRYPOINT))
    return command


def _run_pyinstaller(command: Iterable[str]) -> None:
    """Execute PyInstaller and raise ``BuildError`` on failure."""

    print("[build] invoking:", " ".join(map(str, command)))
    process = subprocess.run(command, check=False)
    if process.returncode != 0:
        raise BuildError(f"PyInstaller exited with status {process.returncode}")


def _maybe_zip_bundle(app_name: str) -> Path | None:
    """Create a portable .zip archive of the bundled directory."""

    bundle_dir = DIST_ROOT / app_name
    if not bundle_dir.exists():
        print(f"[build] warning: bundle directory '{bundle_dir}' missing; skipping zip")
        return None

    archive_path = DIST_ROOT / f"{app_name}-portable"
    if archive_path.exists():
        shutil.rmtree(archive_path)

    archive_file = shutil.make_archive(str(archive_path), "zip", root_dir=bundle_dir)
    return Path(archive_file)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Tenos.ai configurator executable.")
    parser.add_argument(
        "--app-name",
        default=DEFAULT_APP_NAME,
        help="Executable name to emit (defaults to '%(default)s').",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove PyInstaller caches before building.",
    )
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Emit a single-file executable instead of a folder bundle.",
    )
    parser.add_argument(
        "--zip",
        action="store_true",
        help="Create a portable .zip alongside the PyInstaller output.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    _ensure_pyinstaller()

    if args.clean:
        shutil.rmtree(BUILD_ROOT, ignore_errors=True)
        shutil.rmtree(DIST_ROOT / args.app_name, ignore_errors=True)

    command = _build_pyinstaller_command(args)

    try:
        _run_pyinstaller(command)
    except BuildError as exc:  # pragma: no cover - propagated from PyInstaller
        print(f"[build] error: {exc}")
        return 1

    if args.zip and not args.onefile:
        archive = _maybe_zip_bundle(args.app_name)
        if archive:
            print(f"[build] created archive: {archive.relative_to(PROJECT_ROOT)}")

    print(
        "[build] success! Executable located at",
        DIST_ROOT.joinpath(args.app_name, f"{args.app_name}.exe"),
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - manual invocation entry point
    raise SystemExit(main())
