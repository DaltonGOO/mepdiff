# ADR-0005: Revit is the first adapter, and IFC is deferred

- **Status:** Proposed
- **Date:** 2026-08-23

## Context

[ADR-0001](0001-normalised-ir-with-ifc-as-first-adapter.md) made IFC adapter #1
on testability grounds: GitHub-hosted runners have no Revit, so a Revit-first
core would have a test suite that runs on one desktop, quietly nullifying every
quality practice this repository is meant to demonstrate.

That argument is correct about the *core*, and this record does not dispute it.
It reaches too far in one step, though: from "the core must be testable without
Revit" it concluded "the Revit adapter therefore comes last," at M10. That does
not follow, and the code as it stands is the evidence.

**The engine's tests consume snapshot JSON, not source files.** The fixture in
`tests/conftest.py` is built in Python, element by element, with no adapter
involved at all. Nothing in the current suite would change if the IFC adapter
were struck from the roadmap tomorrow, because nothing in it was ever going to
come from IFC. The CI story rests on the IR being constructible and
serialisable, which ADR-0004 delivered — not on which adapter exists.

Three further forces, all of which ADR-0001 either understated or recorded
against itself:

**The people who can evaluate this tool model in Revit.** CONTRIBUTING asks for
design feedback from people who model MEP and says outright that it is worth
more than code. [ADR-0002](0002-collapse-topology-before-diffing.md) records that
degree-based branch detection "needs real files to tune and is a known risk."
[ADR-0003](0003-tiered-identity-matching.md) records that tier 2 is "untunable
without real messy files." Both risks are retired by the same thing: real models
from real MEP modellers. Putting the adapter those people can run at M10 defers
the arrival of that evidence behind nine milestones of work it was supposed to
inform.

**IFC is lossy exactly where the headline claim lives.** ADR-0001 already
concedes that computed engineering values — airflow, pressure drop — are
frequently absent from IFC, and accepts that the first working version must
report pressure drop as unavailable. The README's example output leads with a
downstream airflow rollup. An IFC-first v1 would therefore be weakest at the
thing it advertises, and would stay weak until adapter #2 landed.

**IFC export is itself a Revit chore.** Reaching the tool through IFC means
configuring an export mapping first. That is a step MEP modellers get wrong, and
getting it wrong produces a thin snapshot rather than an error — so the reader
sees a sparse model and blames the tool.

## Decision

**Revit is adapter #1.** The IFC adapter is **deferred, not cancelled**: it comes
off the near roadmap and stays a stated direction, because vendor neutrality is
still worth having and ADR-0001's IR design is what makes it a bolt-on rather
than a rewrite.

**The Revit adapter is a read-only exporter.** It walks the model and emits a
canonical snapshot per ADR-0004. It opens no transaction, writes no parameter,
and modifies nothing. Everything it does is a read, which is what makes it small
enough to be trustworthy without CI.

**All judgement stays in the engine.** The exporter's only job is to transcribe:
elements, connectors, systems, marks, and the flow and pressure values Revit has
already computed. It decides nothing about significance, identity, or change.
Anything it decides is a decision CI cannot test.

**Fixtures come in two kinds, and neither needs Revit to test against:**

- *Synthetic* — snapshots built in Python for the case under test, as
  `tests/conftest.py` already does.
- *Scrubbed* — snapshots exported from real Revit models, reduced to the minimum
  subgraph and stripped of project identity, then committed as JSON.

CI runs on Linux against both, unchanged.

**The exporter is tested where it runs.** A desktop harness against a small
committed `.rvt`, run by hand, plus golden-file comparison of its *output*, which
CI does check. The untested-in-CI boundary is drawn tightly around the one
component that cannot be tested on a GitHub runner.

**Implementation sequence: pyRevit first, .NET add-in second.** A pyRevit
extension gets the exporter into modellers' hands in days rather than weeks, and
pyRevit is already installed across much of the target audience. A signed C#
add-in is how it ships properly once the IR has stopped moving. This part of the
decision is the least settled and the cheapest to revisit — the emitted bytes are
what matter, and both routes emit the same ones.

## Consequences

- **The Python ceiling loses its only justification.** `requires-python =
  ">=3.11,<3.13"` in `pyproject.toml`, the assertion in
  `tests/test_packaging.py`, and the note in CONTRIBUTING all exist solely
  because IfcOpenShell 0.8.x declares `<3.13`. With IFC deferred, nothing holds
  the ceiling. It should be widened when this record is accepted, and the CI
  matrix extended to match — not before, so that the reason for the change is on
  the record first.
- **Windows stops being a courtesy in CI and becomes the primary target.** The
  matrix already covers it; now it covers the platform the adapter runs on.
- **The exporter is not covered by CI, and that is a genuine loss.** It is
  mitigated by keeping the exporter thin and by golden-testing its output, but a
  regression in the exporter reaches a user before it reaches a test. This is the
  real price of the decision and it should not be described as anything smaller.
- **The cross-adapter conformance test from ADR-0001 goes away for now.** That
  test was the mechanism keeping the IR vendor-neutral, and without it Revit's
  model of the world can leak into the IR unchallenged. Two things hold the line
  instead: ADR-0004's IR was written against IFC concepts and still carries them,
  and every new IR field must be reviewed by asking whether an IFC adapter could
  fill it. That is weaker than a test, and it is the risk being accepted.
- **The exporter carries distribution costs the IFC path did not have** — a Revit
  version matrix, an installer, and eventually code signing.
- **Contributors need Revit to work on the adapter**, which narrows the
  contributor pool for that one component. The engine, which is most of the
  project, stays contributable by anyone with Python.
- `Source.adapter` becomes `"revit"` and `source_format` records the Revit
  version, which ADR-0004's provenance model already accommodates.
- The roadmap in the README is reordered when this record is accepted, not while
  it is proposed.

## Alternatives considered

**Keep IFC first (ADR-0001 unchanged).** Vendor-neutral, and the adapter is pure
Python in one repository with no second toolchain. Rejected because the
testability benefit it was chosen for turns out not to depend on it — the fixture
strategy is adapter-independent and always was — while the costs above are real.

**Build both adapters at once.** Keeps the conformance test and reaches both
audiences. Rejected: two adapters and no engine. The engine is the product.

**Design Automation for Revit (Autodesk Platform Services)** to run the exporter
server-side, restoring CI coverage of the one untested component. The most
tempting alternative here, and the only one that addresses the actual loss.
Rejected for now on three grounds: it requires uploading `.rvt` files to
Autodesk's cloud, which sits badly beside CONTRIBUTING's rule about project
models; it costs cloud credits and adds an Autodesk account as a dependency of
the test suite; and it is infrastructure in service of a component that does not
exist yet. Worth revisiting once the exporter is real and stable.

**A Dynamo graph instead of an add-in.** The lowest barrier of all for this
audience. Rejected as the primary route: graphs are hard to version, hard to
review in a pull request, and hard to test — three properties this project has
otherwise been strict about.

**Drop IFC permanently.** Rejected. The deferral costs nothing to keep open, the
IR was designed for it, and vendor neutrality is a real part of the tool's
long-term case.
