"""Shared helpers for coordinating bot settings between Discord UI and configurator."""
from __future__ import annotations

from typing import Dict, Optional

WAN_CHECKPOINT_KEY = "default_wan_checkpoint"
WAN_T2V_HIGH_NOISE_KEY = "default_wan_t2v_high_noise_unet"
WAN_T2V_LOW_NOISE_KEY = "default_wan_t2v_low_noise_unet"
WAN_I2V_HIGH_NOISE_KEY = "default_wan_i2v_high_noise_unet"
WAN_I2V_LOW_NOISE_KEY = "default_wan_i2v_low_noise_unet"

WAN_MODEL_KEYS = (
    WAN_T2V_HIGH_NOISE_KEY,
    WAN_T2V_LOW_NOISE_KEY,
    WAN_I2V_HIGH_NOISE_KEY,
    WAN_I2V_LOW_NOISE_KEY,
)


def sync_wan_checkpoint_alias(settings: Dict[str, object]) -> None:
    """Ensure WAN checkpoint aliases stay in sync for backwards compatibility.

    Historically the WAN default checkpoint lived under ``default_wan_checkpoint``.
    Newer workflows store the active model under ``default_wan_t2v_high_noise_unet``.
    Users may upgrade from older versions that only have one of the keys populated,
    so we mirror whichever value exists to the missing entry.
    """

    if not isinstance(settings, dict):
        return

    wan_high_value = settings.get(WAN_T2V_HIGH_NOISE_KEY)
    wan_checkpoint_value = settings.get(WAN_CHECKPOINT_KEY)

    # Prefer the explicit high-noise UNet value when available.
    canonical_value: Optional[str] = None
    if isinstance(wan_high_value, str) and wan_high_value.strip():
        canonical_value = wan_high_value.strip()
    elif isinstance(wan_checkpoint_value, str) and wan_checkpoint_value.strip():
        canonical_value = wan_checkpoint_value.strip()

    if canonical_value:
        settings[WAN_T2V_HIGH_NOISE_KEY] = canonical_value
        settings[WAN_CHECKPOINT_KEY] = canonical_value
    else:
        # No explicit value available — normalise empty entries to ``None`` so
        # downstream consumers can detect the unset state consistently.
        settings.setdefault(WAN_T2V_HIGH_NOISE_KEY, None)
        settings.setdefault(WAN_CHECKPOINT_KEY, None)


