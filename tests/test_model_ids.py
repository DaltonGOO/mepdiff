"""Synthetic identifier determinism."""

from __future__ import annotations

import pytest

from mepdiff.model.ids import SYNTHETIC_ID_BYTES, synthetic_id


class TestSyntheticId:
    def test_is_deterministic(self) -> None:
        """The whole reason this function exists."""
        assert synthetic_id("port", ["IfcDuctSegment", 0]) == synthetic_id(
            "port", ["IfcDuctSegment", 0]
        )

    def test_distinguishes_different_input(self) -> None:
        assert synthetic_id("port", ["a", 0]) != synthetic_id("port", ["a", 1])

    def test_is_order_sensitive(self) -> None:
        """Port 0 of element A is not port A of element 0."""
        assert synthetic_id("port", ["a", "b"]) != synthetic_id("port", ["b", "a"])

    def test_separator_prevents_ambiguity(self) -> None:
        """Concatenation alone would make ("ab","c") and ("a","bc") collide."""
        assert synthetic_id("n", ["ab", "c"]) != synthetic_id("n", ["a", "bc"])

    def test_prefix_is_legible_and_significant(self) -> None:
        result = synthetic_id("port", ["x"])
        assert result.startswith("port:")
        assert result != synthetic_id("node", ["x"])

    def test_digest_length_matches_declaration(self) -> None:
        digest = synthetic_id("port", ["x"]).partition(":")[2]
        assert len(digest) == SYNTHETIC_ID_BYTES * 2

    def test_none_is_distinct_from_empty_string(self) -> None:
        """A missing mark is not the same fact as a blank mark."""
        assert synthetic_id("n", [None, "x"]) != synthetic_id("n", ["", "x"])

    def test_bool_is_not_rendered_as_int(self) -> None:
        """bool subclasses int; without care True and 1 would collide."""
        assert synthetic_id("n", [True]) != synthetic_id("n", [1])

    def test_float_rendering_is_stable(self) -> None:
        assert synthetic_id("n", [0.1 + 0.2]) == synthetic_id("n", [0.30000000000000004])

    def test_rejects_empty_prefix(self) -> None:
        with pytest.raises(ValueError, match="non-empty prefix"):
            synthetic_id("", ["x"])

    def test_known_value_is_pinned(self) -> None:
        """Guards against an accidental change to the hashing scheme.

        Changing the algorithm changes every synthetic id in every snapshot ever
        written, so it must be a deliberate, schema-versioned decision rather
        than a side effect of refactoring.
        """
        assert synthetic_id("port", ["seg.SEG-1", 0]) == "port:090311629df94bc9"
