"""Canonical form and referential integrity of the snapshot model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mepdiff.model import (
    SCHEMA_VERSION,
    Connection,
    Node,
    NodeKind,
    Point3D,
    Port,
    PortDirection,
    Snapshot,
    Source,
    System,
    SystemClassification,
)

SOURCE = Source(adapter="test", adapter_version="1")


def _node(node_id: str, **overrides: object) -> Node:
    defaults: dict[str, object] = {
        "id": node_id,
        "kind": NodeKind.SEGMENT,
        "source_class": "IfcDuctSegment",
    }
    return Node.model_validate(defaults | overrides)


def _snapshot(**overrides: object) -> Snapshot:
    return Snapshot.model_validate({"source": SOURCE} | overrides)


class TestCanonicalOrder:
    def test_collections_are_stored_in_identifier_order(self) -> None:
        """Adapters traverse source files in whatever order the file happens to
        have; the IR must not inherit that."""
        snapshot = _snapshot(nodes=(_node("z"), _node("a"), _node("m")))
        assert [node.id for node in snapshot.nodes] == ["a", "m", "z"]

    def test_input_order_does_not_affect_the_result(self) -> None:
        forwards = _snapshot(nodes=(_node("a"), _node("b"), _node("c")))
        backwards = _snapshot(nodes=(_node("c"), _node("b"), _node("a")))
        assert forwards == backwards

    def test_connection_endpoints_are_sorted(self) -> None:
        """A join has no direction, so it must serialise the same either way."""
        forwards = Connection(id="c", port_ids=("p1", "p2"))
        backwards = Connection(id="c", port_ids=("p2", "p1"))
        assert forwards.port_ids == ("p1", "p2")
        assert forwards == backwards

    def test_system_ids_are_sorted(self) -> None:
        node = _node("n", system_ids=("s2", "s1"))
        assert node.system_ids == ("s1", "s2")

    def test_property_keys_are_sorted(self) -> None:
        node = _node("n", properties={"zeta": 1, "alpha": 2})
        assert list(node.properties) == ["alpha", "zeta"]

    def test_property_floats_are_quantised(self) -> None:
        node = _node("n", properties={"value": 2.5000000001})
        assert node.properties["value"] == 2.5

    def test_property_scalars_keep_their_types(self) -> None:
        """bool must not decay to int, or a diff reports a spurious change."""
        node = _node("n", properties={"flag": True, "count": 3, "text": "x"})
        assert node.properties["flag"] is True
        assert node.properties["count"] == 3
        assert isinstance(node.properties["count"], int)
        assert node.properties["text"] == "x"


class TestQuantityHandling:
    def test_quantities_are_quantised_on_construction(self) -> None:
        assert _node("n", flow_rate=0.1888000000001).flow_rate == 0.1888

    def test_negative_zero_is_normalised(self) -> None:
        point = Point3D(x=-0.0, y=0.0, z=-0.0)
        assert point == Point3D(x=0.0, y=0.0, z=0.0)

    def test_non_finite_quantity_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="non-finite quantity"):
            _node("n", flow_rate=float("inf"))

    def test_absent_is_distinct_from_zero(self) -> None:
        """The distinction ADR-0001 requires: unknown is not the same as none."""
        assert _node("n").flow_rate is None
        assert _node("n", flow_rate=0.0).flow_rate == 0.0


class TestIntegrity:
    def test_accepts_a_consistent_network(self, sample_network: Snapshot) -> None:
        assert len(sample_network.nodes) == 11
        assert len(sample_network.connections) == 10

    def test_rejects_duplicate_node_ids(self) -> None:
        with pytest.raises(ValidationError, match="duplicate node ids"):
            _snapshot(nodes=(_node("dup"), _node("dup")))

    def test_rejects_duplicate_connection_ids(self) -> None:
        with pytest.raises(ValidationError, match="duplicate connection ids"):
            _snapshot(
                nodes=(_node("n"),),
                ports=(
                    Port(id="p1", node_id="n"),
                    Port(id="p2", node_id="n"),
                    Port(id="p3", node_id="n"),
                ),
                connections=(
                    Connection(id="c", port_ids=("p1", "p2")),
                    Connection(id="c", port_ids=("p1", "p3")),
                ),
            )

    def test_rejects_port_on_unknown_node(self) -> None:
        with pytest.raises(ValidationError, match="dangling node references"):
            _snapshot(nodes=(_node("n"),), ports=(Port(id="p", node_id="ghost"),))

    def test_rejects_connection_to_unknown_port(self) -> None:
        with pytest.raises(ValidationError, match="dangling port references"):
            _snapshot(
                nodes=(_node("n"),),
                ports=(Port(id="p1", node_id="n"),),
                connections=(Connection(id="c", port_ids=("p1", "ghost")),),
            )

    def test_rejects_node_in_unknown_system(self) -> None:
        with pytest.raises(ValidationError, match="dangling system references"):
            _snapshot(nodes=(_node("n", system_ids=("ghost",)),))

    def test_rejects_port_in_unknown_system(self) -> None:
        with pytest.raises(ValidationError, match="dangling system references"):
            _snapshot(
                nodes=(_node("n"),),
                ports=(Port(id="p", node_id="n", system_id="ghost"),),
            )

    def test_rejects_self_connection(self) -> None:
        with pytest.raises(ValidationError, match="to itself"):
            Connection(id="c", port_ids=("p", "p"))

    def test_rejects_duplicate_joins(self) -> None:
        """Two records of one join would double the degree at that point, and
        degree is how M3 decides what counts as a branch."""
        with pytest.raises(ValidationError, match="duplicate connections"):
            _snapshot(
                nodes=(_node("n"),),
                ports=(Port(id="p1", node_id="n"), Port(id="p2", node_id="n")),
                connections=(
                    Connection(id="c1", port_ids=("p1", "p2")),
                    Connection(id="c2", port_ids=("p2", "p1")),
                ),
            )

    def test_rejects_duplicate_system_ids_on_a_node(self) -> None:
        with pytest.raises(ValidationError, match="duplicate system_ids"):
            _node("n", system_ids=("s", "s"))

    def test_error_message_is_truncated(self) -> None:
        """A broken adapter produces thousands; the traceback must stay usable."""
        with pytest.raises(ValidationError, match="and 5 more"):
            _snapshot(nodes=tuple(_node("dup") for _ in range(11)))


class TestSchemaVersion:
    def test_defaults_to_the_current_version(self) -> None:
        assert _snapshot().schema_version == SCHEMA_VERSION

    def test_accepts_an_unknown_minor(self) -> None:
        """Additive changes must not lock an older reader out."""
        assert _snapshot(schema_version="1.999").schema_version == "1.999"

    def test_rejects_an_unknown_major(self) -> None:
        with pytest.raises(ValidationError, match="not readable by this build"):
            _snapshot(schema_version="2.0")


class TestModelDiscipline:
    def test_snapshots_are_immutable(self) -> None:
        """A snapshot describes a moment that has already happened."""
        snapshot = _snapshot()
        with pytest.raises(ValidationError):
            snapshot.schema_version = "1.1"  # type: ignore[misc]

    def test_unknown_fields_are_rejected(self) -> None:
        """A misspelled field in an adapter must fail at the boundary."""
        with pytest.raises(ValidationError):
            _node("n", flowrate=1.0)

    def test_empty_identifier_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _node("")

    def test_source_class_is_preserved_verbatim(self, sample_network: Snapshot) -> None:
        """Adapter decisions stay auditable."""
        vav = next(node for node in sample_network.nodes if node.mark == "VAV-12")
        assert vav.source_class == "IfcAirTerminalBox"
        assert vav.kind is NodeKind.TERMINAL_BOX


class TestDefaults:
    def test_unclassified_system_says_so(self) -> None:
        assert System(id="s").classification is SystemClassification.UNKNOWN

    def test_undeclared_port_direction_says_so(self) -> None:
        """Exporters commonly omit this; M4 must be able to tell."""
        assert Port(id="p", node_id="n").direction is PortDirection.UNKNOWN
