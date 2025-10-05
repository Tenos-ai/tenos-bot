"""Utilities for handling semantic-like version comparison."""
from __future__ import annotations

import re
from typing import Iterable, Optional, Tuple


_VERSION_PART_RE = re.compile(r"\d+")


def _extract_numeric_parts(tag: str) -> Tuple[int, ...]:
    """Return a tuple of integers extracted from *tag*.

    The helper tolerates prefixes such as ``v`` or ``release-`` and
    ignores any non-numeric components so that human friendly tags like
    ``v1.2.3`` or ``release_2024-01-05`` can be compared reliably.
    """
    numbers = [int(match.group(0)) for match in _VERSION_PART_RE.finditer(tag)]
    return tuple(numbers)


def normalise_tag(tag: Optional[str]) -> Optional[Tuple[int, ...]]:
    """Convert a tag or version string into a tuple for comparisons."""
    if tag is None:
        return None
    tag = tag.strip()
    if not tag:
        return None
    numeric_parts = _extract_numeric_parts(tag)
    return numeric_parts or None


def _pad_tuple(values: Iterable[int], length: int) -> Tuple[int, ...]:
    parts = tuple(values)
    if len(parts) >= length:
        return parts
    return parts + (0,) * (length - len(parts))


def is_remote_version_newer(remote_tag: Optional[str], local_version: Optional[str]) -> bool:
    """Return ``True`` if *remote_tag* represents a newer version."""
    remote_norm = normalise_tag(remote_tag)
    local_norm = normalise_tag(local_version)

    if remote_norm is None:
        return False
    if local_norm is None:
        return True

    # Compare tuples by padding to the same length so that ``(1, 2)`` is
    # considered older than ``(1, 2, 1)``.
    max_len = max(len(remote_norm), len(local_norm))
    remote_padded = _pad_tuple(remote_norm, max_len)
    local_padded = _pad_tuple(local_norm, max_len)
    return remote_padded > local_padded

# End of file
