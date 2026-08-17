"""The snapshot intermediate representation.

A :class:`Snapshot` is what an adapter produces and what every later pass
consumes. It is a flat, normalised description of a distribution network: which
elements exist, where their connection points are, and which of those points are
joined. It deliberately contains no derived facts -- no flow direction, no
downstream totals, no notion of a branch. Those are computed, and computing them
is M3 and M4's job.

Two properties are load-bearing and are enforced here rather than left to
convention:

**Canonical form.** Collections are stored in identifier order, mappings in key
order, and quantities quantised, so that the same model always produces the same
bytes. Golden-file tests compare exact bytes, and a snapshot that changes
without the model changing is worthless as a handover record.

**Referential integrity.** A port must belong to a real element; a connection
must join real ports. Adapters are where the messy work happens, and a dangling
reference caught at construction is a clear error message, where the same
reference caught three passes later is a mystery.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator

from mepdiff.model.enums import NodeKind, PortDirection, SystemClassification
from mepdiff.model.units import quantise

__all__ = [
    "SCHEMA_VERSION",
    "Connection",
    "Identifier",
    "Node",
    "Point3D",
    "Port",
    "Properties",
    "PropertyValue",
    "Quantity",
    "Snapshot",
    "Source",
    "System",
]

SCHEMA_VERSION = "1.0"
"""Version of the on-disk snapshot format.

Major version changes on any edit that makes an older reader wrong -- a removed
field, a changed unit, a redefined enum member. Minor version changes on purely
additive edits. Readers reject an unknown major and accept an unknown minor,
because the whole point of an archival format is that a snapshot written today
is still readable when someone goes looking for it during a dispute.
"""

# How many offending values an integrity error names before truncating. A broken
# adapter produces thousands; a traceback listing all of them helps nobody.
_MAX_REPORTED = 5


PropertyValue = str | int | float | bool | None
"""What may live in a free-form property bag.

Scalars only, deliberately. Nested structures would make canonical ordering and
diffing recursive problems, and nothing in the source formats needs them: an IFC
property set and a Revit parameter list are both flat.
"""


def _canonical_properties(value: dict[str, PropertyValue]) -> dict[str, PropertyValue]:
    """Sort keys and quantise float values."""
    return {
        key: quantise(item) if isinstance(item, float) else item
        for key, item in sorted(value.items())
    }


Identifier = Annotated[str, Field(min_length=1)]
"""A non-empty identifier, unique within its collection."""

Quantity = Annotated[float, AfterValidator(quantise)]
"""A physical quantity in SI base units.

Always SI: m3/s, Pa, m. See :mod:`mepdiff.model.units` for why, and note that
``None`` means *the source did not provide this*, which is a different statement
from ``0.0``. Reporting an undetermined value as zero would be a lie the diff
engine cannot later detect.
"""

Properties = Annotated[dict[str, PropertyValue], AfterValidator(_canonical_properties)]
"""Source-specific values with no promoted field of their own."""


class _Base(BaseModel):
    """Shared configuration.

    Frozen because a snapshot describes a moment that has already happened.
    ``extra="forbid"`` because a misspelled field in an adapter should fail at
    the boundary, not silently vanish and surface as a missing property in a
    report three milestones later.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")


class Point3D(_Base):
    """A location in metres, in the source's project coordinate system.

    Used only as a weak signal for structural matching (ADR-0003, tier 2).
    mepdiff answers topological questions, so geometry is never authoritative
    here -- it breaks ties, it does not decide them.
    """

    x: Quantity
    y: Quantity
    z: Quantity


class Source(_Base):
    """Provenance of a snapshot.

    Note what is absent: no file path, no timestamp, no user name. Each would
    make two exports of the same model produce different bytes, and the file
    path would additionally leak a directory structure into a format meant to be
    committed to a public repository. ``digest`` identifies the input exactly
    without carrying any of that.
    """

    adapter: str
    """Which adapter produced this, e.g. ``"ifc"``."""

    adapter_version: str
    """Version of the adapter, so a changed reading can be attributed."""

    source_format: str | None = None
    """Schema of the input, e.g. ``"IFC4"``."""

    application: str | None = None
    """Authoring application recorded in the input, e.g. ``"Revit 2025"``."""

    digest: str | None = None
    """Hex digest of the input file, identifying it without naming it."""


class System(_Base):
    """A distribution system: the thing a set of elements collectively forms."""

    id: Identifier
    classification: SystemClassification = SystemClassification.UNKNOWN
    name: str | None = None
    source_id: str | None = None
    """Durable identifier from the source, where it has one."""

    properties: Properties = Field(default_factory=dict)


class Node(_Base):
    """One element of the network."""

    id: Identifier
    kind: NodeKind
    source_class: str
    """The source's own classification, verbatim: ``"IfcAirTerminalBox"``.

    Preserved for reporting and debugging. Nothing downstream may branch on it --
    that is what :attr:`kind` is for -- but discarding it would make an adapter's
    decisions unauditable.
    """

    source_id: str | None = None
    """IFC ``GlobalId`` or Revit ``UniqueId``. The tier-0 matching key (ADR-0003).

    Optional because it is genuinely often absent, and because pretending
    otherwise would push adapters into inventing one.
    """

    name: str | None = None

    mark: str | None = None
    """The human-assigned tag: ``"VAV-12"``. The tier-1 matching key (ADR-0003).

    Stable precisely because a person maintains it, which is what makes it more
    trustworthy than a machine identifier across a model rebuild.
    """

    system_ids: tuple[Identifier, ...] = ()
    placement: Point3D | None = None

    flow_rate: Quantity | None = None
    """Design airflow in m3/s. ``None`` if the source did not provide it."""

    pressure_drop: Quantity | None = None
    """Pressure drop in Pa. ``None`` if the source did not provide it.

    Frequently ``None`` for IFC input; ADR-0001 requires reporting that absence
    honestly rather than computing a substitute.
    """

    length: Quantity | None = None
    """Run length in m, for segments. Aggregated into skeleton edges in M3."""

    properties: Properties = Field(default_factory=dict)

    @field_validator("system_ids", mode="after")
    @classmethod
    def _canonicalise_system_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError(f"duplicate system_ids: {sorted(value)}")
        return tuple(sorted(value))


class Port(_Base):
    """A connection point on a :class:`Node`.

    Ports are modelled explicitly rather than collapsed into element-to-element
    edges because *which* port carries a connection is the difference between a
    supply and a return branch, and that distinction is the whole subject of
    this tool.
    """

    id: Identifier
    node_id: Identifier
    direction: PortDirection = PortDirection.UNKNOWN
    """What the source declared. A hint, not an authority -- exporters commonly
    emit ``UNKNOWN``, and M4 derives real orientation from the graph."""

    system_id: Identifier | None = None
    name: str | None = None
    source_id: str | None = None
    properties: Properties = Field(default_factory=dict)


class Connection(_Base):
    """A join between two ports.

    Stored undirected, with the endpoint pair sorted, because a connection has no
    inherent direction -- the source's declared flow direction lives on the ports.
    Sorting makes the same physical join serialise identically regardless of
    which end an adapter happened to walk first.
    """

    id: Identifier
    port_ids: tuple[Identifier, Identifier]

    @field_validator("port_ids", mode="after")
    @classmethod
    def _canonicalise_pair(cls, value: tuple[str, str]) -> tuple[str, str]:
        first, second = sorted(value)
        return (first, second)

    @model_validator(mode="after")
    def _reject_self_connection(self) -> Connection:
        if self.port_ids[0] == self.port_ids[1]:
            raise ValueError(f"connection {self.id!r} joins port {self.port_ids[0]!r} to itself")
        return self


class Snapshot(_Base):
    """A complete, canonical description of a network at one point in time."""

    schema_version: str = SCHEMA_VERSION
    source: Source
    systems: tuple[System, ...] = ()
    nodes: tuple[Node, ...] = ()
    ports: tuple[Port, ...] = ()
    connections: tuple[Connection, ...] = ()

    @field_validator("schema_version", mode="after")
    @classmethod
    def _check_readable(cls, value: str) -> str:
        """Accept an unknown minor, reject an unknown major."""
        major = value.partition(".")[0]
        expected = SCHEMA_VERSION.partition(".")[0]
        if major != expected:
            raise ValueError(
                f"snapshot schema version {value!r} is not readable by this build, "
                f"which supports {expected}.x"
            )
        return value

    @field_validator("systems", "nodes", "ports", "connections", mode="after")
    @classmethod
    def _canonicalise_order(cls, value: tuple[Any, ...]) -> tuple[Any, ...]:
        """Store collections in identifier order.

        This is what makes the format independent of the order an adapter
        happened to traverse the source file in.
        """
        return tuple(sorted(value, key=lambda item: str(item.id)))

    @model_validator(mode="after")
    def _check_integrity(self) -> Snapshot:
        system_ids = _unique_ids(self.systems, "system")
        node_ids = _unique_ids(self.nodes, "node")
        port_ids = _unique_ids(self.ports, "port")
        _unique_ids(self.connections, "connection")

        _require_known(
            ((port.id, port.node_id) for port in self.ports),
            known=node_ids,
            what="port",
            referencing="node",
        )
        _require_known(
            ((port.id, port.system_id) for port in self.ports if port.system_id is not None),
            known=system_ids,
            what="port",
            referencing="system",
        )
        _require_known(
            ((node.id, system_id) for node in self.nodes for system_id in node.system_ids),
            known=system_ids,
            what="node",
            referencing="system",
        )
        _require_known(
            (
                (connection.id, port_id)
                for connection in self.connections
                for port_id in connection.port_ids
            ),
            known=port_ids,
            what="connection",
            referencing="port",
        )

        _reject_duplicate_joins(self.connections)
        return self


def _unique_ids(items: tuple[Any, ...], what: str) -> frozenset[str]:
    """Return the id set, rejecting duplicates."""
    seen: set[str] = set()
    duplicates: list[str] = []
    for item in items:
        if item.id in seen:
            duplicates.append(str(item.id))
        seen.add(item.id)
    if duplicates:
        raise ValueError(f"duplicate {what} ids: {_summarise(sorted(duplicates))}")
    return frozenset(seen)


def _require_known(
    references: Any,
    *,
    known: frozenset[str],
    what: str,
    referencing: str,
) -> None:
    """Reject references to identifiers that are not present."""
    dangling = sorted(
        f"{what} {holder!r} -> {referencing} {target!r}"
        for holder, target in references
        if target not in known
    )
    if dangling:
        raise ValueError(f"dangling {referencing} references: {_summarise(dangling)}")


def _reject_duplicate_joins(connections: tuple[Connection, ...]) -> None:
    """Reject two connections describing the same physical join.

    Duplicates would double-count degree, and degree is how M3 decides what a
    branch point is -- so this silently corrupts the skeleton rather than
    failing.
    """
    seen: set[tuple[str, str]] = set()
    duplicates: list[str] = []
    for connection in connections:
        if connection.port_ids in seen:
            duplicates.append(f"{connection.id!r} {connection.port_ids}")
        seen.add(connection.port_ids)
    if duplicates:
        raise ValueError(f"duplicate connections: {_summarise(sorted(duplicates))}")


def _summarise(items: list[str]) -> str:
    shown = ", ".join(items[:_MAX_REPORTED])
    remaining = len(items) - _MAX_REPORTED
    return f"{shown} (and {remaining} more)" if remaining > 0 else shown
