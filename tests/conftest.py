"""A small but structurally real air-side network, shared across the suite.

Deliberately not a toy pair of boxes. It has a trunk, a tee that branches, two
VAV boxes, and two diffusers -- which is the smallest shape that exercises the
things mepdiff actually has to reason about: a branch point (M3 collapses runs
around it), a path from equipment to terminal (M4 walks it), and marks that a
matcher can key on (M5).

Later milestones should extend this fixture rather than inventing their own, so
that the golden files tell a continuous story.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from mepdiff.model import (
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
    cfm_to_si,
    inches_water_gauge_to_si,
)

SYSTEM_ID = "sys.SA-1"


@dataclass(frozen=True)
class _Element:
    """Declarative spec for one node and its ports."""

    id: str
    kind: NodeKind
    source_class: str
    ports: tuple[PortDirection, ...]
    mark: str | None = None
    flow_cfm: float | None = None
    pressure_drop_inwg: float | None = None
    length_m: float | None = None
    at: tuple[float, float, float] = (0.0, 0.0, 0.0)
    properties: dict[str, str | int | float | bool | None] = field(default_factory=dict)


_IN = PortDirection.SINK
_OUT = PortDirection.SOURCE

# AHU-1 -> SEG-1 -> TEE-1 branches to two VAVs, each feeding one diffuser.
_ELEMENTS: tuple[_Element, ...] = (
    _Element(
        id="ahu.AHU-1",
        kind=NodeKind.EQUIPMENT,
        source_class="IfcUnitaryEquipment",
        ports=(_OUT,),
        mark="AHU-1",
        flow_cfm=800.0,
        at=(0.0, 0.0, 3.0),
        properties={"Level": "L1", "Manufacturer": "Acme"},
    ),
    _Element(
        id="seg.SEG-1",
        kind=NodeKind.SEGMENT,
        source_class="IfcDuctSegment",
        ports=(_IN, _OUT),
        length_m=6.0,
        pressure_drop_inwg=0.12,
        at=(3.0, 0.0, 3.0),
    ),
    _Element(
        id="fit.TEE-1",
        kind=NodeKind.FITTING,
        source_class="IfcDuctFitting",
        ports=(_IN, _OUT, _OUT),
        pressure_drop_inwg=0.05,
        at=(6.0, 0.0, 3.0),
    ),
    _Element(
        id="seg.SEG-2",
        kind=NodeKind.SEGMENT,
        source_class="IfcDuctSegment",
        ports=(_IN, _OUT),
        length_m=4.0,
        pressure_drop_inwg=0.08,
        at=(6.0, 3.0, 3.0),
    ),
    _Element(
        id="seg.SEG-3",
        kind=NodeKind.SEGMENT,
        source_class="IfcDuctSegment",
        ports=(_IN, _OUT),
        length_m=4.0,
        pressure_drop_inwg=0.08,
        at=(6.0, -3.0, 3.0),
    ),
    _Element(
        id="box.VAV-12",
        kind=NodeKind.TERMINAL_BOX,
        source_class="IfcAirTerminalBox",
        ports=(_IN, _OUT),
        mark="VAV-12",
        flow_cfm=400.0,
        pressure_drop_inwg=0.35,
        at=(6.0, 6.0, 3.0),
        properties={"Level": "L1"},
    ),
    _Element(
        id="box.VAV-13",
        kind=NodeKind.TERMINAL_BOX,
        source_class="IfcAirTerminalBox",
        ports=(_IN, _OUT),
        mark="VAV-13",
        flow_cfm=400.0,
        pressure_drop_inwg=0.35,
        at=(6.0, -6.0, 3.0),
        properties={"Level": "L1"},
    ),
    _Element(
        id="seg.SEG-4",
        kind=NodeKind.SEGMENT,
        source_class="IfcDuctSegment",
        ports=(_IN, _OUT),
        length_m=2.5,
        at=(6.0, 8.0, 3.0),
    ),
    _Element(
        id="seg.SEG-5",
        kind=NodeKind.SEGMENT,
        source_class="IfcDuctSegment",
        ports=(_IN, _OUT),
        length_m=2.5,
        at=(6.0, -8.0, 3.0),
    ),
    _Element(
        id="term.DIFF-101",
        kind=NodeKind.TERMINAL,
        source_class="IfcAirTerminal",
        ports=(_IN,),
        mark="DIFF-101",
        flow_cfm=400.0,
        at=(6.0, 10.0, 2.8),
    ),
    _Element(
        id="term.DIFF-102",
        kind=NodeKind.TERMINAL,
        source_class="IfcAirTerminal",
        ports=(_IN,),
        mark="DIFF-102",
        flow_cfm=400.0,
        at=(6.0, -10.0, 2.8),
    ),
)

# (from, to) as (element id, port index) pairs.
_JOINS: tuple[tuple[tuple[str, int], tuple[str, int]], ...] = (
    (("ahu.AHU-1", 0), ("seg.SEG-1", 0)),
    (("seg.SEG-1", 1), ("fit.TEE-1", 0)),
    (("fit.TEE-1", 1), ("seg.SEG-2", 0)),
    (("fit.TEE-1", 2), ("seg.SEG-3", 0)),
    (("seg.SEG-2", 1), ("box.VAV-12", 0)),
    (("seg.SEG-3", 1), ("box.VAV-13", 0)),
    (("box.VAV-12", 1), ("seg.SEG-4", 0)),
    (("box.VAV-13", 1), ("seg.SEG-5", 0)),
    (("seg.SEG-4", 1), ("term.DIFF-101", 0)),
    (("seg.SEG-5", 1), ("term.DIFF-102", 0)),
)


def _port_id(element_id: str, index: int) -> str:
    return f"{element_id}#p{index}"


def build_sample_network() -> Snapshot:
    """Construct the shared fixture network."""
    nodes: list[Node] = []
    ports: list[Port] = []

    for element in _ELEMENTS:
        nodes.append(
            Node(
                id=element.id,
                kind=element.kind,
                source_class=element.source_class,
                source_id=f"gid-{element.id}",
                name=element.mark or element.id,
                mark=element.mark,
                system_ids=(SYSTEM_ID,),
                placement=Point3D(x=element.at[0], y=element.at[1], z=element.at[2]),
                flow_rate=None if element.flow_cfm is None else cfm_to_si(element.flow_cfm),
                pressure_drop=(
                    None
                    if element.pressure_drop_inwg is None
                    else inches_water_gauge_to_si(element.pressure_drop_inwg)
                ),
                length=element.length_m,
                properties=element.properties,
            )
        )
        for index, direction in enumerate(element.ports):
            ports.append(
                Port(
                    id=_port_id(element.id, index),
                    node_id=element.id,
                    direction=direction,
                    system_id=SYSTEM_ID,
                )
            )

    connections = tuple(
        Connection(
            id=f"conn.{a_id}#{a_index}--{b_id}#{b_index}",
            port_ids=(_port_id(a_id, a_index), _port_id(b_id, b_index)),
        )
        for (a_id, a_index), (b_id, b_index) in _JOINS
    )

    return Snapshot(
        source=Source(
            adapter="fixture",
            adapter_version="1",
            source_format="IFC4",
            application="mepdiff test fixture",
            digest="0" * 64,
        ),
        systems=(
            System(
                id=SYSTEM_ID,
                classification=SystemClassification.SUPPLY_AIR,
                name="SA-1",
                source_id="gid-sys-SA-1",
            ),
        ),
        nodes=tuple(nodes),
        ports=tuple(ports),
        connections=connections,
    )


@pytest.fixture
def sample_network() -> Snapshot:
    return build_sample_network()


# ---------------------------------------------------------------------------
# Golden-file support
# ---------------------------------------------------------------------------

GOLDEN_DIR = Path(__file__).parent / "fixtures"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--regen-golden",
        action="store_true",
        default=False,
        help="Rewrite golden files from current behaviour, then skip their tests.",
    )


@pytest.fixture
def golden(request: pytest.FixtureRequest) -> Callable[[str, str], None]:
    """Compare text against a committed golden file.

    Regenerate with ``pytest --regen-golden`` -- and then read the resulting
    diff. That diff is the clearest available description of what a change
    actually did, and reviewers will read it as the specification.
    """
    regenerate = bool(request.config.getoption("--regen-golden"))

    def check(actual: str, name: str) -> None:
        path = GOLDEN_DIR / name
        if regenerate:
            path.parent.mkdir(parents=True, exist_ok=True)
            # newline="" keeps LF on Windows; the repository is LF-only.
            path.write_text(actual, encoding="utf-8", newline="")
            pytest.skip(f"regenerated golden file {name}")
        if not path.is_file():
            raise AssertionError(f"golden file {name} is missing; run pytest --regen-golden")
        assert actual == path.read_text(encoding="utf-8"), f"output differs from golden file {name}"

    return check
