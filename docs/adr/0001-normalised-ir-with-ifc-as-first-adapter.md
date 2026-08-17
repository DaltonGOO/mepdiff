# ADR-0001: A normalised IR, with IFC as the first adapter

- **Status:** Accepted
- **Date:** 2026-08-16

## Context

The obvious first question for this project is "which format — IFC, or Revit, or
a project database?" It is the wrong first question. Format choice is an *input
adapter* concern. If a format is chosen first, its quirks get baked into the
core, and the second adapter becomes a rewrite.

The real constraint on the choice is testability. This project intends to use CI
seriously: every pull request should run the diff against committed fixtures and
prove it did not regress. That rules out a Revit-first core, because
GitHub-hosted runners have no Revit, no licence server, and no headless mode. A
Revit-first project would have a test suite that only runs on one desktop, which
quietly nullifies every quality practice the repository is meant to demonstrate.

Set against that, IFC is lossy. Export settings vary, and computed engineering
values — airflow, pressure drop — are frequently absent, whereas the authoring
tool knows them exactly.

## Decision

The project is a normalised topology **intermediate representation** plus the
passes over it (skeleton, match, analyse, diff, report). Formats are adapters
that produce the IR and nothing more.

**IFC is adapter #1**, via IfcOpenShell, because it makes the engine testable in
CI with committed fixtures and gives the tool a vendor-neutral audience.

**A Revit add-in is adapter #2**, emitting the IR directly from the connector
graph rather than round-tripping through IFC. That recovers the fidelity IFC
loses — computed flow, pressure drop, authoritative system assignment — without
the core ever depending on Revit.

The IR is not merely internal. It is deterministic, ordered, and text, so a
snapshot can be committed per milestone and any two points in a project's
history diffed. That archival property is a requirement of the IR's design, not
a side effect.

## Consequences

- The engine is fully testable on Linux CI with no proprietary software.
- The first working version reports airflow and connectivity confidently, and
  must report pressure drop as *unavailable* whenever the source did not carry
  it. Honest absence is required; inventing values is not acceptable in a tool
  meant for handover.
- Computing pressure drop from geometry — Darcy-Weisbach plus fitting loss
  coefficients — is explicitly out of scope for now. It is an ASHRAE-table rabbit
  hole that would consume the project, and it becomes far less necessary once
  adapter #2 lands.
- **The supported Python range is `>=3.11,<3.13`.** IfcOpenShell 0.8.x declares
  `>=3.9,<3.13`, so 3.12 is the ceiling for the whole project, including modules
  that do not themselves import it. This is enforced in `pyproject.toml` and
  asserted in the test suite so it fails loudly rather than confusingly.
- Two adapters must be kept honest against each other. The same physical model
  exported both ways should produce IRs that differ only where IFC genuinely
  lost information. That is a future conformance test, and a real maintenance
  cost we are accepting.

## Alternatives considered

**Revit-first.** Best data, and the users are already there. Rejected on
testability: no CI, no committed fixtures, no reproducible bug reports from
contributors.

**A project/vendor database as the first source.** Considered and dropped for
now — no such source is currently available to the maintainer, and a live
database gives no natural snapshot boundary, which is what the archival and
history goals depend on.

**Diff the formats directly, with no IR.** Simplest to start. Rejected because
it makes the second adapter a rewrite and offers nowhere to put the analysis
passes, which are the actual product.
