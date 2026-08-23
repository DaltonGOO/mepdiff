"""Canonical serialisation: determinism, losslessness, and on-disk form."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from mepdiff.model import (
    Connection,
    Node,
    NodeKind,
    Port,
    Snapshot,
    Source,
    dumps,
    json_schema,
    loads,
    read,
    write,
)

SOURCE = Source(adapter="test", adapter_version="1")


def _node(node_id: str, **overrides: object) -> Node:
    defaults: dict[str, object] = {
        "id": node_id,
        "kind": NodeKind.SEGMENT,
        "source_class": "IfcDuctSegment",
    }
    return Node.model_validate(defaults | overrides)


class TestDeterminism:
    def test_repeated_serialisation_is_identical(self, sample_network: Snapshot) -> None:
        assert dumps(sample_network) == dumps(sample_network)

    def test_construction_order_does_not_change_the_bytes(self) -> None:
        """The guarantee the golden-file strategy rests on."""
        forwards = Snapshot(
            source=SOURCE,
            nodes=(_node("a"), _node("b"), _node("c")),
            ports=(Port(id="p1", node_id="a"), Port(id="p2", node_id="b")),
            connections=(Connection(id="c1", port_ids=("p1", "p2")),),
        )
        backwards = Snapshot(
            source=SOURCE,
            nodes=(_node("c"), _node("b"), _node("a")),
            ports=(Port(id="p2", node_id="b"), Port(id="p1", node_id="a")),
            connections=(Connection(id="c1", port_ids=("p2", "p1")),),
        )
        assert dumps(forwards) == dumps(backwards)

    def test_object_keys_are_sorted(self, sample_network: Snapshot) -> None:
        payload = json.loads(dumps(sample_network))
        assert list(payload) == sorted(payload)

    def test_output_ends_with_a_newline(self, sample_network: Snapshot) -> None:
        """POSIX text file convention; also keeps git from reporting no-newline."""
        assert dumps(sample_network).endswith("}\n")

    def test_no_timestamp_or_path_leaks_into_the_payload(self, sample_network: Snapshot) -> None:
        """Either would make two exports of one model differ. See Source's docstring."""
        payload = json.loads(dumps(sample_network))
        assert set(payload["source"]) <= {
            "adapter",
            "adapter_version",
            "source_format",
            "application",
            "digest",
        }


class TestRoundTrip:
    def test_sample_network_survives_intact(self, sample_network: Snapshot) -> None:
        assert loads(dumps(sample_network)) == sample_network

    def test_reserialises_to_the_same_bytes(self, sample_network: Snapshot) -> None:
        once = dumps(sample_network)
        assert dumps(loads(once)) == once

    def test_empty_snapshot_survives(self) -> None:
        snapshot = Snapshot(source=SOURCE)
        assert loads(dumps(snapshot)) == snapshot

    def test_unicode_is_preserved_and_not_escaped(self) -> None:
        snapshot = Snapshot(source=SOURCE, nodes=(_node("n", name="Zuluft-Gerät"),))
        text = dumps(snapshot)
        assert "Zuluft-Gerät" in text
        assert loads(text) == snapshot


class TestPruning:
    def test_absent_values_are_omitted(self) -> None:
        payload = json.loads(dumps(Snapshot(source=SOURCE, nodes=(_node("n"),))))
        assert "flow_rate" not in payload["nodes"][0]
        assert "properties" not in payload["nodes"][0]

    def test_empty_collections_are_omitted(self) -> None:
        payload = json.loads(dumps(Snapshot(source=SOURCE)))
        assert "nodes" not in payload

    @pytest.mark.parametrize("value", [0.0, -0.0])
    def test_zero_is_not_treated_as_absent(self, value: float) -> None:
        """The distinction ADR-0001 turns on: a real zero must survive pruning."""
        payload = json.loads(dumps(Snapshot(source=SOURCE, nodes=(_node("n", flow_rate=value),))))
        assert payload["nodes"][0]["flow_rate"] == 0.0

    def test_falsy_property_values_are_not_pruned(self) -> None:
        node = _node("n", properties={"flag": False, "text": "", "count": 0})
        payload = json.loads(dumps(Snapshot(source=SOURCE, nodes=(node,))))
        assert payload["nodes"][0]["properties"] == {"flag": False, "text": "", "count": 0}

    def test_pruning_is_lossless(self) -> None:
        """Everything omitted must have an empty default to be restored from."""
        snapshot = Snapshot(source=SOURCE, nodes=(_node("n"),))
        assert loads(dumps(snapshot)) == snapshot


class TestRejections:
    @pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
    def test_non_standard_json_constants_are_refused(self, literal: str) -> None:
        """`json` accepts these by default; an interchange format must not."""
        with pytest.raises(ValueError, match="non-standard JSON constant"):
            loads(f'{{"source": {{"adapter": "t", "adapter_version": "1"}}, "x": {literal}}}')

    def test_malformed_json_is_refused(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            loads("{not json")


class TestFileIO:
    def test_write_then_read_round_trips(self, sample_network: Snapshot, tmp_path: Path) -> None:
        path = tmp_path / "snapshot.json"
        write(sample_network, path)
        assert read(path) == sample_network

    def test_written_file_uses_lf_even_on_windows(
        self, sample_network: Snapshot, tmp_path: Path
    ) -> None:
        """Without newline="" this writes CRLF on Windows, and every golden test
        fails on one half of the CI matrix for reasons unrelated to the code."""
        path = tmp_path / "snapshot.json"
        write(sample_network, path)
        raw = path.read_bytes()
        assert b"\r\n" not in raw
        assert raw.endswith(b"}\n")

    def test_written_file_is_utf8(self, tmp_path: Path) -> None:
        path = tmp_path / "snapshot.json"
        write(Snapshot(source=SOURCE, nodes=(_node("n", name="Gerät"),)), path)
        assert "Gerät" in path.read_bytes().decode("utf-8")


class TestJsonSchema:
    def test_publishes_a_schema_for_the_archived_format(self) -> None:
        """So a snapshot written today is checkable without this exact build."""
        schema = json_schema()
        assert schema["type"] == "object"
        assert "source" in schema["properties"]
        assert "nodes" in schema["properties"]


class TestGolden:
    def test_sample_network_matches_the_committed_form(
        self, sample_network: Snapshot, golden: Callable[[str, str], None]
    ) -> None:
        golden(dumps(sample_network), "snapshot/sample_network.json")
