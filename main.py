"""Convenience entrypoint for launching the Tenos.ai bot."""
from __future__ import annotations

import runpy
from pathlib import Path


def _resolve_main_bot() -> Path:
    here = Path(__file__).resolve()
    candidate = here.with_name("main_bot.py")
    if not candidate.exists():
        raise FileNotFoundError(f"Expected to find main_bot.py alongside {here}.")
    return candidate


if __name__ == "__main__":
    runpy.run_path(str(_resolve_main_bot()), run_name="__main__")
