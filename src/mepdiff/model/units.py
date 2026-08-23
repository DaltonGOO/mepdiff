"""Canonical units, and the float discipline the snapshot format depends on.

**The IR stores SI base units, always.** Airflow in m3/s, pressure in Pa, length
in m. Adapters convert on the way in; reports convert on the way out. Nothing in
between carries a unit, because a value that might be CFM and might be m3/s is a
bug waiting for a coordination meeting to find it.

This costs readability in the raw JSON -- ``0.188778`` is less legible than
``400`` -- and that is an accepted trade. A mixed-unit archival format cannot be
compared across snapshots without knowing which exporter wrote each one, which
defeats the purpose of having an archival format.

Quantisation is a separate concern from diff tolerance. Here we make the *same
input produce the same bytes*, by clipping the noise that unit conversion leaves
in the low bits of a double. Deciding that 400.0 CFM and 400.2 CFM are "the same
airflow" is a reporting judgement and belongs to the diff engine, not here.
"""

from __future__ import annotations

import math

__all__ = [
    "CUBIC_METRES_PER_SECOND_PER_CFM",
    "METRES_PER_FOOT",
    "METRES_PER_INCH",
    "PASCALS_PER_INCH_WATER_GAUGE",
    "QUANTISE_PLACES",
    "cfm_to_si",
    "inches_water_gauge_to_si",
    "quantise",
    "si_to_cfm",
    "si_to_inches_water_gauge",
]

QUANTISE_PLACES = 9
"""Decimal places retained for every stored quantity.

At SI scale this is far finer than any real measurement -- a nanometre of length,
roughly two millionths of a CFM -- so it discards nothing an engineer could
observe, while removing the 1e-16 residue that unit conversion leaves behind.
"""

# Exact by definition of the international foot and inch.
METRES_PER_FOOT = 0.3048
METRES_PER_INCH = 0.0254

# 1 CFM = 1 ft3/min = 0.3048^3 m3 / 60 s.
CUBIC_METRES_PER_SECOND_PER_CFM = METRES_PER_FOOT**3 / 60.0

# 1 in. w.g. at the conventional 4 degC water density used by ASHRAE.
PASCALS_PER_INCH_WATER_GAUGE = 249.0889


def quantise(value: float) -> float:
    """Reduce ``value`` to its canonical stored form.

    Rounds to :data:`QUANTISE_PLACES` and collapses negative zero, which is a
    distinct IEEE-754 value that serialises as ``-0.0`` and would otherwise make
    two identical models produce different bytes.

    Raises:
        ValueError: if ``value`` is NaN or infinite. Neither has a JSON
            representation, and both indicate an adapter computed something it
            should have reported as absent instead.
    """
    if not math.isfinite(value):
        raise ValueError(
            f"non-finite quantity: {value!r}. A value that could not be determined "
            f"must be represented as None, not as NaN or infinity."
        )
    rounded = round(value, QUANTISE_PLACES)
    # `rounded == 0` is true for both 0.0 and -0.0; normalise to positive zero.
    return 0.0 if rounded == 0 else rounded


def cfm_to_si(cfm: float) -> float:
    """Cubic feet per minute to m3/s."""
    return quantise(cfm * CUBIC_METRES_PER_SECOND_PER_CFM)


def si_to_cfm(cubic_metres_per_second: float) -> float:
    """m3/s to cubic feet per minute. For reporting only."""
    return cubic_metres_per_second / CUBIC_METRES_PER_SECOND_PER_CFM


def inches_water_gauge_to_si(inches_water_gauge: float) -> float:
    """Inches water gauge to Pa."""
    return quantise(inches_water_gauge * PASCALS_PER_INCH_WATER_GAUGE)


def si_to_inches_water_gauge(pascals: float) -> float:
    """Pa to inches water gauge. For reporting only."""
    return pascals / PASCALS_PER_INCH_WATER_GAUGE
