"""Helpers for comparing semantic-ish version tags."""
from __future__ import annotations

import re
from typing import Optional, Tuple

_VERSION_CAPTURE = re.compile(r"(?P<digits>\d+(?:[._-]\d+)*)")


def _extract_digits(version: str) -> Tuple[int, ...]:
    parts = re.split(r"[._-]", version)
    numeric_parts = []
    for part in parts:
        if part.isdigit():
            numeric_parts.append(int(part))
        else:
            digits = re.findall(r"\d+", part)
            if not digits:
                break
            numeric_parts.append(int(digits[0]))
    return tuple(numeric_parts)


def normalise_tag(tag: Optional[str]) -> Optional[str]:
    """Normalise a git tag or dotted version string to plain numbers."""
    if not tag:
        return None
    tag = tag.strip()
    if not tag:
        return None
    if tag.lower().startswith("release-"):
        tag = tag.split("release-", 1)[1]
    if tag.startswith("v") or tag.startswith("V"):
        tag = tag[1:]
    match = _VERSION_CAPTURE.search(tag)
    if match:
        digits = match.group("digits")
        return digits.replace("_", ".").replace("-", ".")
    return tag


def is_remote_version_newer(remote_tag: Optional[str], current_version: Optional[str]) -> bool:
    """Return True if the remote tag represents a newer version than the current."""
    remote_norm = normalise_tag(remote_tag)
    if remote_norm is None:
        return False

    current_norm = normalise_tag(current_version)
    if current_norm is None:
        return True

    remote_tuple = _extract_digits(remote_norm)
    current_tuple = _extract_digits(current_norm)

    if remote_tuple and current_tuple:
        return remote_tuple > current_tuple

    return remote_norm > current_norm
