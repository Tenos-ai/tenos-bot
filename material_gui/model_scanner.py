"""Utilities for scanning model directories for the configurator."""
from __future__ import annotations

import json
import os
import traceback
from pathlib import Path
from typing import Dict, List


def _safe_listdir(directory: str | os.PathLike[str]) -> list[str]:
    """Return a sorted list of file names for ``directory``.

    The helper guards against missing directories and common ``OSError``
    issues while maintaining the previous logging behaviour.
    """

    path = Path(directory)
    if not path.exists():
        raise FileNotFoundError(directory)

    return sorted((entry.name for entry in path.iterdir()), key=str.lower)


def scan_models(model_directory: str | os.PathLike[str]) -> Dict[str, List[str]]:
    """Scan for Flux model files in the specified directory."""

    models: Dict[str, List[str]] = {"safetensors": [], "sft": [], "gguf": []}

    try:
        for filename in _safe_listdir(model_directory):
            lower_filename = filename.lower()
            if lower_filename.endswith(".safetensors"):
                models["safetensors"].append(filename)
            elif lower_filename.endswith(".sft"):
                models["sft"].append(filename)
            elif lower_filename.endswith(".gguf"):
                models["gguf"].append(filename)
    except FileNotFoundError:
        print(
            f"ModelScanner Warning: Flux Model directory does not exist: {model_directory}"
        )
    except OSError as exc:
        print(
            "ModelScanner Error accessing Flux model directory "
            f"{model_directory}: {exc}"
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"ModelScanner Unexpected error scanning Flux models: {exc}")
        traceback.print_exc()

    return models


def _load_favorites(output_file: str) -> list[str]:
    """Load the ``favorites`` list from an existing JSON file if present."""

    if not os.path.exists(output_file):
        return []

    try:
        with open(output_file, "r", encoding="utf-8") as file:
            current_models_data = json.load(file)
    except (json.JSONDecodeError, OSError) as exc:
        print(
            "ModelScanner Warning: Error reading current Flux models file "
            f"({output_file}): {exc}. Favorites might be lost."
        )
        return []
    except Exception as exc:  # pragma: no cover - defensive logging
        print(
            "ModelScanner Warning: Unexpected error reading "
            f"{output_file}: {exc}. Favorites might be lost."
        )
        return []

    favorites = current_models_data.get("favorites", [])
    if isinstance(favorites, list):
        return [str(favorite) for favorite in favorites if isinstance(favorite, str)]

    print(
        "ModelScanner Warning: 'favorites' in "
        f"{output_file} is not a list. Ignoring."
    )
    return []


def update_models_list(config_path: str, output_file: str) -> None:
    """Update the Flux models list from the configured directory."""

    print(f"ModelScanner: Updating Flux models list ({output_file})...")

    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"ModelScanner Error reading config file {config_path}: {exc}")
        return
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"ModelScanner Unexpected error in update_models_list: {exc}")
        traceback.print_exc()
        return

    model_directory = config.get("MODELS", {}).get("MODEL_FILES")
    if not model_directory:
        print(
            "ModelScanner Error: MODEL_FILES path not found in config for Flux models."
        )
        return

    models = scan_models(model_directory)
    models["favorites"] = _load_favorites(output_file)

    try:
        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(models, file, indent=2)
    except OSError as exc:
        print(
            "ModelScanner Error writing Flux models file "
            f"{output_file}: {exc}"
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        print(
            "ModelScanner Unexpected error writing "
            f"{output_file}: {exc}"
        )


def scan_checkpoints(
    checkpoint_directory: str | os.PathLike[str],
) -> Dict[str, List[str]]:
    """Scan for SDXL checkpoint files in the specified directory."""

    checkpoints: Dict[str, List[str]] = {"checkpoints": []}
    checkpoint_extensions = (".safetensors", ".ckpt", ".pth")

    try:
        for filename in _safe_listdir(checkpoint_directory):
            lower_filename = filename.lower()
            if lower_filename.endswith(checkpoint_extensions):
                checkpoints["checkpoints"].append(filename)
    except FileNotFoundError:
        print(
            "ModelScanner Warning: SDXL Checkpoint directory does not exist: "
            f"{checkpoint_directory}"
        )
    except OSError as exc:
        print(
            "ModelScanner Error accessing SDXL checkpoint directory "
            f"{checkpoint_directory}: {exc}"
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"ModelScanner Unexpected error scanning SDXL checkpoints: {exc}")
        traceback.print_exc()

    checkpoints["checkpoints"].sort(key=str.lower)
    return checkpoints


def _load_checkpoint_favorites(output_file: str) -> list[str]:
    if not os.path.exists(output_file):
        return []

    try:
        with open(output_file, "r", encoding="utf-8") as file:
            current_checkpoints_data = json.load(file)
    except (json.JSONDecodeError, OSError) as exc:
        print(
            "ModelScanner Warning: Error reading current SDXL checkpoints file "
            f"({output_file}): {exc}. Favorites might be lost."
        )
        return []
    except Exception as exc:  # pragma: no cover - defensive logging
        print(
            "ModelScanner Warning: Unexpected error reading "
            f"{output_file} (checkpoints): {exc}. Favorites might be lost."
        )
        return []

    favorites = current_checkpoints_data.get("favorites", [])
    if isinstance(favorites, list):
        return [str(favorite) for favorite in favorites if isinstance(favorite, str)]

    print(
        "ModelScanner Warning: 'favorites' in "
        f"{output_file} (checkpoints) is not a list. Ignoring."
    )
    return []


def update_checkpoints_list(config_path: str, output_file: str) -> None:
    """Update the SDXL checkpoints list from the configured directory."""

    print(f"ModelScanner: Updating SDXL checkpoints list ({output_file})...")

    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            config_data = json.load(config_file)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"ModelScanner Error reading config file {config_path}: {exc}")
        return
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"ModelScanner Unexpected error in update_checkpoints_list: {exc}")
        traceback.print_exc()
        return

    checkpoint_directories: list[str] = []
    checkpoint_directory = config_data.get("MODELS", {}).get("CHECKPOINTS_FOLDER")
    if checkpoint_directory:
        checkpoint_directories.append(checkpoint_directory)

    qwen_directory = config_data.get("QWEN", {}).get("MODEL_FILES")
    if qwen_directory and qwen_directory not in checkpoint_directories:
        checkpoint_directories.append(qwen_directory)

    if not checkpoint_directories:
        print(
            "ModelScanner Error: No checkpoint directories configured for SDXL/"
            "Qwen models."
        )
        return

    aggregated: Dict[str, List[str]] = {"checkpoints": []}
    for directory in checkpoint_directories:
        data = scan_checkpoints(directory)
        for item in data.get("checkpoints", []):
            if item not in aggregated["checkpoints"]:
                aggregated["checkpoints"].append(item)

    aggregated["checkpoints"].sort(key=str.lower)
    aggregated["favorites"] = _load_checkpoint_favorites(output_file)

    try:
        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(aggregated, file, indent=2)
    except OSError as exc:
        print(
            "ModelScanner Error writing SDXL checkpoints file "
            f"{output_file}: {exc}"
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        print(
            "ModelScanner Unexpected error writing {output_file} (checkpoints):"
            f" {exc}"
        )


def scan_clip_files(config_path: str, output_file: str) -> None:
    """Scan for CLIP files and categorize by size."""

    print(f"ModelScanner: Updating CLIP list ({output_file})...")

    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            config_data = json.load(config_file)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"ModelScanner Error reading config file {config_path}: {exc}")
        return
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"ModelScanner Unexpected error updating CLIP list: {exc}")
        traceback.print_exc()
        return

    clip_directories: list[str] = []
    clip_directory = config_data.get("CLIP", {}).get("CLIP_FILES")
    if clip_directory:
        clip_directories.append(clip_directory)

    qwen_clip_directory = config_data.get("QWEN", {}).get("CLIP_FILES")
    if qwen_clip_directory and qwen_clip_directory not in clip_directories:
        clip_directories.append(qwen_clip_directory)

    if not clip_directories:
        print("ModelScanner Error: CLIP directories not configured in config.json.")
        return

    clip_files = {"t5": [], "clip_L": []}

    for directory in clip_directories:
        try:
            for filename in _safe_listdir(directory):
                lower_filename = filename.lower()
                if lower_filename.endswith(".t5"):  # Example extension for T5 models
                    clip_files["t5"].append(filename)
                elif lower_filename.endswith(".clip"):
                    clip_files["clip_L"].append(filename)
        except FileNotFoundError:
            print(f"ModelScanner Error: CLIP directory does not exist: {directory}")
        except OSError as exc:
            print(f"ModelScanner Error accessing CLIP directory {directory}: {exc}")
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"ModelScanner Unexpected error scanning CLIP directory: {exc}")
            traceback.print_exc()

    clip_files["t5"].sort(key=str.lower)
    clip_files["clip_L"].sort(key=str.lower)

    favorites = {"t5": [], "clip_L": []}
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as file:
                current_clip_data = json.load(file)
            for key in favorites:
                fav_values = current_clip_data.get("favorites", {}).get(key, [])
                if isinstance(fav_values, list):
                    favorites[key] = [
                        str(fav) for fav in fav_values if isinstance(fav, str)
                    ]
        except (json.JSONDecodeError, OSError) as exc:
            print(
                "ModelScanner Warning: Error reading current CLIP list file "
                f"({output_file}): {exc}. Favorites might be lost."
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            print(
                "ModelScanner Warning: Unexpected error reading CLIP list file "
                f"{output_file}: {exc}. Favorites might be lost."
            )

    clip_files["favorites"] = favorites

    try:
        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(clip_files, file, indent=2)
    except OSError as exc:
        print(f"ModelScanner Error writing CLIP list file {output_file}: {exc}")
    except Exception as exc:  # pragma: no cover - defensive logging
        print(
            "ModelScanner Unexpected error writing CLIP list file "
            f"{output_file}: {exc}"
        )


__all__ = [
    "scan_models",
    "update_models_list",
    "scan_checkpoints",
    "update_checkpoints_list",
    "scan_clip_files",
]
