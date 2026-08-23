# Architecture decision records

mepdiff is mostly design decisions. What counts as a change, what counts as the
same element, and what counts as noise are judgement calls that a future
contributor would otherwise re-litigate from scratch — so they get written down.

One file per decision, numbered, never renumbered. Supersede rather than rewrite:
if a decision changes, add a new record and mark the old one `Superseded by
ADR-NNNN`. The history is the point.

Start from [`0000-template.md`](0000-template.md).

| ADR | Title | Status |
|---|---|---|
| [0001](0001-normalised-ir-with-ifc-as-first-adapter.md) | A normalised IR, with IFC as the first adapter | Accepted |
| [0002](0002-collapse-topology-before-diffing.md) | Collapse topology to a skeleton before diffing | Accepted |
| [0003](0003-tiered-identity-matching.md) | Tiered identity matching with explicit confidence | Accepted |
| [0004](0004-canonical-snapshot-representation.md) | A canonical, self-validating snapshot representation | Accepted |
