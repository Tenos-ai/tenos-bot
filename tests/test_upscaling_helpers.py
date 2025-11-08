import os
import sys
import tempfile
import types
import unittest
from unittest import mock

if "PIL" not in sys.modules:
    pil_stub = types.ModuleType("PIL")
    pil_image_stub = types.ModuleType("PIL.Image")

    def _stub_open(*args, **kwargs):  # pragma: no cover - placeholder for pillow dependency
        raise NotImplementedError("Pillow is not installed in the test environment")

    pil_image_stub.open = _stub_open
    pil_stub.Image = pil_image_stub
    sys.modules["PIL"] = pil_stub
    sys.modules["PIL.Image"] = pil_image_stub

if "discord" not in sys.modules:
    discord_stub = types.ModuleType("discord")

    class _DummySelectOption:
        def __init__(self, label=None, value=None, default=None, *args, **kwargs):  # pragma: no cover - stub
            self.label = label
            self.value = value
            self.default = default

    discord_stub.SelectOption = _DummySelectOption
    sys.modules["discord"] = discord_stub

if "numpy" not in sys.modules:
    numpy_stub = types.ModuleType("numpy")

    def _arange(start, stop=None, step=1.0):  # pragma: no cover - stub
        if stop is None:
            stop = float(start)
            start = 0.0
        values = []
        current = float(start)
        step = float(step)
        comparator = (lambda a, b: a < b) if step > 0 else (lambda a, b: a > b)
        while comparator(current, float(stop)) or abs(current - float(stop)) < 1e-9:
            values.append(current)
            current += step
        return values

    numpy_stub.arange = _arange
    sys.modules["numpy"] = numpy_stub

if "websocket_client" not in sys.modules:
    websocket_stub = types.ModuleType("websocket_client")

    class _StubWebsocketClient:  # pragma: no cover - stub
        def __init__(self, *args, **kwargs):
            raise ValueError("Websocket client is unavailable in tests")

    websocket_stub.WebsocketClient = _StubWebsocketClient
    sys.modules["websocket_client"] = websocket_stub

import upscaling

from upscaling import (
    _match_available_option,
    _resolve_upscale_model_choice,
    _sanitize_override,
    _select_preferred_option,
)


class UpscalingHelperTests(unittest.TestCase):
    def test_sanitize_override_filters_none_like_values(self) -> None:
        self.assertIsNone(_sanitize_override(None))
        self.assertIsNone(_sanitize_override(""))
        self.assertIsNone(_sanitize_override(" none "))
        self.assertIsNone(_sanitize_override("AUTO"))
        self.assertIsNone(_sanitize_override("automatic"))
        self.assertIsNone(_sanitize_override("Default"))

    def test_sanitize_override_preserves_valid_value(self) -> None:
        self.assertEqual(_sanitize_override("  MyModel.safetensors  "), "MyModel.safetensors")

    def test_match_available_option_exact_match(self) -> None:
        resolved, exact = _match_available_option("4x-UltraSharp.pth", ["4x-UltraSharp.pth", "Another.pth"])
        self.assertEqual(resolved, "4x-UltraSharp.pth")
        self.assertTrue(exact)

    def test_match_available_option_case_insensitive(self) -> None:
        resolved, exact = _match_available_option("4x-ultrasharp.pth", ["4x-UltraSharp.pth"])
        self.assertEqual(resolved, "4x-UltraSharp.pth")
        self.assertTrue(exact)

    def test_match_available_option_matches_by_basename(self) -> None:
        resolved, exact = _match_available_option(
            "4x-ultrasharp.pth",
            ["models/upscale/4x-UltraSharp.pth", "other.pth"],
        )
        self.assertEqual(resolved, "models/upscale/4x-UltraSharp.pth")
        self.assertTrue(exact)

    def test_match_available_option_falls_back_to_first_available(self) -> None:
        resolved, exact = _match_available_option("missing.pth", ["first.pth", "second.pth"])
        self.assertEqual(resolved, "first.pth")
        self.assertFalse(exact)

    def test_match_available_option_returns_requested_when_no_options(self) -> None:
        resolved, exact = _match_available_option("missing.pth", [])
        self.assertEqual(resolved, "missing.pth")
        self.assertFalse(exact)

    def test_select_preferred_option_prefers_override(self) -> None:
        resolved = _select_preferred_option(
            ["override.safetensors", "template.safetensors"],
            ["override.safetensors", "other.safetensors"],
            description="model",
        )
        self.assertEqual(resolved, "override.safetensors")

    def test_select_preferred_option_falls_back_to_template(self) -> None:
        resolved = _select_preferred_option(
            ["missing.safetensors", "template.safetensors"],
            ["template.safetensors", "fallback.safetensors"],
            description="model",
        )
        self.assertEqual(resolved, "template.safetensors")

    def test_select_preferred_option_defaults_to_available_when_all_missing(self) -> None:
        resolved = _select_preferred_option(
            ["missing.safetensors", "another_missing.safetensors"],
            ["fallback.safetensors", "second.safetensors"],
            description="model",
        )
        self.assertEqual(resolved, "fallback.safetensors")

    def test_select_preferred_option_returns_candidate_without_options(self) -> None:
        resolved = _select_preferred_option(
            ["preferred.safetensors", None],
            [],
            description="model",
        )
        self.assertEqual(resolved, "preferred.safetensors")


class UpscaleModelResolutionTests(unittest.TestCase):
    def test_resolve_upscale_model_choice_falls_back_to_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            template_path = os.path.join(tmp_dir, "4x-UltraSharp.pth")
            with open(template_path, "w", encoding="utf-8"):
                pass

            with mock.patch.object(upscaling, "UPSCALE_MODELS_ROOT", tmp_dir, create=True):
                choice = _resolve_upscale_model_choice("COMBO", "4x-UltraSharp.pth", [])
                self.assertEqual(choice, "4x-UltraSharp.pth")

    def test_resolve_upscale_model_choice_prefers_existing_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            preferred_path = os.path.join(tmp_dir, "RealESRGAN_x4plus.pth")
            template_path = os.path.join(tmp_dir, "4x-UltraSharp.pth")
            for path in (preferred_path, template_path):
                with open(path, "w", encoding="utf-8"):
                    pass

            with mock.patch.object(upscaling, "UPSCALE_MODELS_ROOT", tmp_dir, create=True):
                choice = _resolve_upscale_model_choice(
                    "RealESRGAN_x4plus.pth",
                    "4x-UltraSharp.pth",
                    [],
                )
                self.assertEqual(choice, "RealESRGAN_x4plus.pth")

    def test_resolve_upscale_model_choice_returns_none_when_no_valid_candidates(self) -> None:
        with mock.patch.object(upscaling, "UPSCALE_MODELS_ROOT", None, create=True):
            choice = _resolve_upscale_model_choice("COMBO", None, [])
            self.assertIsNone(choice)

    def test_resolve_upscale_model_choice_uses_available_options_when_candidates_invalid(self) -> None:
        available = [
            "COMBO",
            "4x-UltraSharp.pth",
            "RealESRGAN_x4plus.pth",
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            fallback_path = os.path.join(tmp_dir, "4x-UltraSharp.pth")
            with open(fallback_path, "w", encoding="utf-8"):
                pass

            with mock.patch.object(upscaling, "UPSCALE_MODELS_ROOT", tmp_dir, create=True):
                choice = _resolve_upscale_model_choice("COMBO", "COMBO", available)
                self.assertEqual(choice, "4x-UltraSharp.pth")

    def test_resolve_upscale_model_choice_reads_local_directory_when_no_api_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            local_model = os.path.join(tmp_dir, "4x-UltraSharp.pth")
            with open(local_model, "w", encoding="utf-8"):
                pass

            with mock.patch.object(upscaling, "UPSCALE_MODELS_ROOT", tmp_dir, create=True):
                choice = _resolve_upscale_model_choice("COMBO", "COMBO", [])
                self.assertEqual(choice, "4x-UltraSharp.pth")


if __name__ == "__main__":
    unittest.main()
