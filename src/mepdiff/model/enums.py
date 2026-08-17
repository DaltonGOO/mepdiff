"""Adapter-agnostic vocabularies.

These deliberately do not mirror any one source format. An IFC adapter maps
``IfcAirTerminalBox`` to :attr:`NodeKind.TERMINAL_BOX`; a Revit adapter maps its
own category to the same member. The original classification is never discarded
-- it is preserved verbatim in ``Node.source_class`` -- but nothing downstream of
an adapter is permitted to branch on it.

Every enum carries an explicit ``UNKNOWN`` member. Adapters encounter elements
they do not recognise, and the honest representation of that is a value that
says so, not a plausible-looking guess.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["NodeKind", "PortDirection", "SystemClassification"]


class NodeKind(StrEnum):
    """What a network element *is*, for the purposes of topology.

    The distinction that matters most here is between elements a person names
    and reasons about (equipment, terminals, boxes, controllers) and elements
    that merely connect them (segments, fittings). ADR-0002 collapses the latter
    into edges, so this enum is what the significance test consults.
    """

    EQUIPMENT = "equipment"
    """Air handling units, rooftop units, unitary equipment."""

    FAN = "fan"
    COIL = "coil"
    FILTER = "filter"

    TERMINAL = "terminal"
    """Diffusers, grilles, registers -- where air enters or leaves the space."""

    TERMINAL_BOX = "terminal_box"
    """VAV and CAV boxes."""

    FLOW_CONTROLLER = "flow_controller"
    """Dampers and valves: elements that are named and deliberately placed."""

    SEGMENT = "segment"
    """A run of duct. Collapsed into a skeleton edge (ADR-0002)."""

    FITTING = "fitting"
    """Elbows, tees, transitions. Collapsed into a skeleton edge (ADR-0002)."""

    ACCESSORY = "accessory"
    """Silencers, sensors, and other in-line devices."""

    UNKNOWN = "unknown"


class PortDirection(StrEnum):
    """Flow direction declared at a connection point.

    Mirrors the intent of IFC's ``IfcFlowDirectionEnum``. This is what a source
    *declares*, which is not always what is true -- exporters frequently emit
    ``UNKNOWN``. Deriving actual orientation from the graph is M4's problem, and
    it must treat this as a hint rather than an authority.
    """

    SOURCE = "source"
    SINK = "sink"
    SOURCE_AND_SINK = "source_and_sink"
    UNKNOWN = "unknown"


class SystemClassification(StrEnum):
    """What a distribution system carries.

    Air-side only, per ADR-0001's v1 scope. Hydronic, plumbing, and electrical
    classifications are deliberately absent rather than stubbed: an empty member
    invites adapters to map things into it prematurely.
    """

    SUPPLY_AIR = "supply_air"
    RETURN_AIR = "return_air"
    EXHAUST_AIR = "exhaust_air"
    OUTSIDE_AIR = "outside_air"
    RELIEF_AIR = "relief_air"
    OTHER = "other"
    UNKNOWN = "unknown"
