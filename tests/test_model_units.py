"""Quantisation and unit conversion."""

from __future__ import annotations

import math

import pytest

from mepdiff.model.units import (
    QUANTISE_PLACES,
    cfm_to_si,
    inches_water_gauge_to_si,
    quantise,
    si_to_cfm,
    si_to_inches_water_gauge,
)


class TestQuantise:
    def test_clips_conversion_residue(self) -> None:
        """The point of the exercise: kill the low bits, keep the value."""
        assert quantise(2.5000000001) == 2.5

    def test_preserves_significant_precision(self) -> None:
        assert quantise(0.123456789) == 0.123456789

    def test_normalises_negative_zero(self) -> None:
        """-0.0 and 0.0 are distinct doubles that serialise differently."""
        result = quantise(-0.0)
        assert result == 0.0
        assert math.copysign(1.0, result) == 1.0

    def test_leaves_ordinary_values_alone(self) -> None:
        assert quantise(400.0) == 400.0
        assert quantise(-3.25) == -3.25

    @pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
    def test_rejects_non_finite(self, value: float) -> None:
        """An undeterminable value must be reported as absent, not as NaN."""
        with pytest.raises(ValueError, match="non-finite quantity"):
            quantise(value)

    def test_is_idempotent(self) -> None:
        """Re-quantising a stored value must never move it, or round-trips drift."""
        for raw in (1 / 3, 400.0, 1e-12, -2.7182818284590452, 1e9 + 0.5):
            once = quantise(raw)
            assert quantise(once) == once

    def test_documented_precision_is_what_is_applied(self) -> None:
        below = 10.0 ** -(QUANTISE_PLACES + 1)
        assert quantise(below) == 0.0
        assert quantise(10.0**-QUANTISE_PLACES) != 0.0


class TestConversions:
    def test_cfm_conversion_matches_definition(self) -> None:
        # 1 ft3/min = 0.3048^3 m3 / 60 s
        assert cfm_to_si(1.0) == pytest.approx(0.3048**3 / 60.0)

    def test_typical_vav_airflow(self) -> None:
        assert cfm_to_si(400.0) == pytest.approx(0.18878, abs=1e-5)

    def test_typical_branch_pressure_drop(self) -> None:
        assert inches_water_gauge_to_si(0.8) == pytest.approx(199.27, abs=1e-2)

    @pytest.mark.parametrize("cfm", [0.0, 1.0, 400.0, 12500.0])
    def test_airflow_round_trips(self, cfm: float) -> None:
        assert si_to_cfm(cfm_to_si(cfm)) == pytest.approx(cfm)

    @pytest.mark.parametrize("inwg", [0.0, 0.8, 2.1])
    def test_pressure_round_trips(self, inwg: float) -> None:
        assert si_to_inches_water_gauge(inches_water_gauge_to_si(inwg)) == pytest.approx(inwg)

    def test_conversions_quantise_their_output(self) -> None:
        """Converted values enter the IR already canonical."""
        assert cfm_to_si(1.0) == quantise(cfm_to_si(1.0))
