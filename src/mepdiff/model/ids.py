"""Deterministic identifier synthesis for elements the source did not identify.

Ports in particular are routinely unidentified: IFC exporters reissue them on
every write, and Revit does not expose a durable identifier for a connector at
all. Something must name them, and that something has to produce the same answer
on every run, on every platform, for the same input.

A note on what these identifiers are *not*. A synthetic id is stable **within a
snapshot**, not across snapshots -- it is derived from content, so anything that
edits the element changes its id. Matching the same element between two
snapshots is a separate problem with its own tiered solution (ADR-0003), and
nothing here should be mistaken for solving it. Using a synthetic id as a
matching key would silently report every edited element as a deletion plus an
addition.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

__all__ = ["SYNTHETIC_ID_BYTES", "synthetic_id"]

SYNTHETIC_ID_BYTES = 8
"""Digest length, giving 16 hex characters.

Sized against the birthday bound rather than preimage resistance -- this is a
uniqueness device, not a security control. Collisions become plausible around
2**32 elements in one snapshot, which is several orders of magnitude beyond any
real model, and :class:`~mepdiff.model.snapshot.Snapshot` rejects duplicate ids
outright, so a collision fails loudly rather than corrupting a diff.
"""

# ASCII unit separator: not legal in the element names, marks, or class names
# these identifiers are built from, so it cannot be forged by a crafted name.
_SEPARATOR = "\x1f"

# ASCII null, likewise unforgeable, standing for a component that is absent.
_ABSENT = "\x00"


def _render(part: object) -> str:
    """Render one component to a platform-stable string.

    ``repr`` is used for floats deliberately: CPython guarantees the shortest
    representation that round-trips, which is stable across platforms, whereas
    ``str`` formatting of floats has historically not been.
    """
    if part is None:
        # Not the empty string: "this element has no mark" and "this element's
        # mark is blank" are different facts about a model, and collapsing them
        # would give two genuinely different elements the same identifier.
        return _ABSENT
    if isinstance(part, float):
        return repr(part)
    if isinstance(part, bool):
        # Checked before int, since bool is a subclass of int.
        return "true" if part else "false"
    return str(part)


def synthetic_id(prefix: str, parts: Iterable[object]) -> str:
    """Build a deterministic identifier from ``parts``.

    Args:
        prefix: Short tag naming what kind of thing this is, e.g. ``"port"``.
            Kept in the clear so identifiers stay legible when debugging.
        parts: Components that together distinguish this element from its
            siblings. Order is significant.

    Returns:
        ``"{prefix}:{16 hex digits}"``.
    """
    if not prefix:
        raise ValueError("synthetic_id requires a non-empty prefix")

    payload = _SEPARATOR.join(_render(part) for part in parts)
    digest = hashlib.blake2b(payload.encode("utf-8"), digest_size=SYNTHETIC_ID_BYTES)
    return f"{prefix}:{digest.hexdigest()}"
