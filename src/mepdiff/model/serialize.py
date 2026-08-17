"""Canonical JSON serialisation.

The guarantee this module exists to provide: **the same snapshot always produces
the same bytes**, on any platform, on any supported Python. Everything else here
follows from that.

The output is meant to be committed. It is indented rather than minified,
key-ordered, UTF-8, and LF-terminated, so that a reviewer looking at two
milestones in a pull request sees a readable line diff rather than one enormous
changed line.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mepdiff.model.snapshot import Snapshot

__all__ = ["dumps", "json_schema", "loads", "read", "write"]

_INDENT = 2
_SEPARATORS = (",", ": ")


def _reject_constant(name: str) -> Any:
    """Refuse the JSON extensions that are not actually JSON.

    ``json`` accepts bare ``NaN`` and ``Infinity`` by default. They have no place
    in an interchange format, and their presence means an upstream computation
    produced a value it should have reported as absent.
    """
    raise ValueError(
        f"snapshot contains the non-standard JSON constant {name!r}. "
        f"An undetermined quantity must be represented as null."
    )


def _is_empty(value: Any) -> bool:
    """Whether a value carries no information and can be omitted.

    Deliberately not a truthiness test: ``0``, ``0.0``, ``False``, and ``""`` are
    all meaningful values that must survive.
    """
    return value is None or (isinstance(value, dict | list) and len(value) == 0)


def _prune(value: Any) -> Any:
    """Drop nulls and empty containers from mappings, recursively.

    Every field this removes has an empty default, so reading the pruned document
    reconstructs the original snapshot exactly -- the round-trip test in the
    suite is what holds this claim honest.

    Without it, a realistic snapshot repeats ``"pressure_drop": null`` and
    ``"properties": {}`` across tens of thousands of elements, which buries the
    lines that actually changed.
    """
    if isinstance(value, dict):
        pruned = {key: _prune(item) for key, item in value.items()}
        return {key: item for key, item in pruned.items() if not _is_empty(item)}
    if isinstance(value, list):
        return [_prune(item) for item in value]
    return value


def dumps(snapshot: Snapshot) -> str:
    """Serialise ``snapshot`` to canonical JSON text, ending in a newline."""
    payload = _prune(snapshot.model_dump(mode="json"))
    text = json.dumps(
        payload,
        indent=_INDENT,
        separators=_SEPARATORS,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    )
    return text + "\n"


def loads(text: str) -> Snapshot:
    """Parse canonical JSON text into a :class:`Snapshot`."""
    payload = json.loads(text, parse_constant=_reject_constant)
    return Snapshot.model_validate(payload)


def write(snapshot: Snapshot, path: Path) -> None:
    """Write ``snapshot`` to ``path``.

    ``newline=""`` suppresses the platform line-ending translation that would
    otherwise silently write CRLF on Windows and break byte-for-byte comparison
    against a file written on Linux.
    """
    path.write_text(dumps(snapshot), encoding="utf-8", newline="")


def read(path: Path) -> Snapshot:
    """Read a snapshot from ``path``."""
    return loads(path.read_text(encoding="utf-8"))


def json_schema() -> dict[str, Any]:
    """JSON Schema for the snapshot format.

    Published so that a snapshot archived today can be validated by something
    other than this exact build years from now, which is the point of committing
    them at all.
    """
    return Snapshot.model_json_schema()
