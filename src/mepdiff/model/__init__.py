"""The snapshot intermediate representation and its canonical serialisation.

This is the contract between adapters and everything downstream. See ADR-0001
for why the IR exists at all, and ADR-0004 for how it is shaped.
"""

from __future__ import annotations

from mepdiff.model.enums import NodeKind, PortDirection, SystemClassification
from mepdiff.model.ids import synthetic_id
from mepdiff.model.serialize import dumps, json_schema, loads, read, write
from mepdiff.model.snapshot import (
    SCHEMA_VERSION,
    Connection,
    Node,
    Point3D,
    Port,
    Snapshot,
    Source,
    System,
)
from mepdiff.model.units import cfm_to_si, inches_water_gauge_to_si, quantise

__all__ = [
    "SCHEMA_VERSION",
    "Connection",
    "Node",
    "NodeKind",
    "Point3D",
    "Port",
    "PortDirection",
    "Snapshot",
    "Source",
    "System",
    "SystemClassification",
    "cfm_to_si",
    "dumps",
    "inches_water_gauge_to_si",
    "json_schema",
    "loads",
    "quantise",
    "read",
    "synthetic_id",
    "write",
]
