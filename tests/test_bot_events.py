import os

import pytest

from bot_events import _option_matches


@pytest.mark.parametrize(
    "selected, options, expected",
    [
        ("model.safetensors", ["model.safetensors"], True),
        ("Model.SafeTensors", ["model.safetensors"], True),
        ("model.safetensors", ["models/checkpoints/model.safetensors"], True),
        ("models/upscale/4x-UltraSharp.pth", ["4x-ultrasharp.pth"], True),
        ("missing.pth", ["other.pth"], False),
        ("", ["model.safetensors"], False),
        ("model.safetensors", [], False),
    ],
)
def test_option_matches(selected, options, expected):
    assert _option_matches(selected, options) is expected


def test_option_matches_skips_non_strings():
    options = ["model.safetensors", 123, None, os]
    assert _option_matches("model.safetensors", options) is True
