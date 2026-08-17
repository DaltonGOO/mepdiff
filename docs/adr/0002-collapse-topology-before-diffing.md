# ADR-0002: Collapse topology to a skeleton before diffing

- **Status:** Accepted
- **Date:** 2026-08-16

## Context

A duct network in a real model is mostly segments and fittings. Those are the
elements that churn hardest between snapshots: reroute a run by 300 mm and every
segment is re-cut, every elbow regenerated, every identifier reissued. A diff
computed over the raw element graph reports tens of thousands of changes for a
revision that an engineer would summarise in one sentence.

A tool that reports everything is equivalent to a tool that reports nothing. The
noise problem is not a polish item to address after the diff works — it decides
whether the diff is worth computing at all.

Separately, the changes we actually want to report are not element-level facts.
"This branch's pressure drop went from 0.8 to 2.1 in. w.g." is a property of a
*run* between two meaningful points, not of any one fitting in it.

## Decision

Before diffing, reduce the network to a **topology skeleton**.

A node survives into the skeleton if it is *significant*:

- equipment (air handlers, fans, coils, heat recovery),
- terminals (diffusers, grilles, registers) and terminal boxes (VAV/CAV),
- flow controllers a human names and cares about (dampers, valves),
- branch points, i.e. connection degree > 2,
- system boundaries.

Every intervening run of segments and fittings collapses into a **single
skeleton edge** carrying aggregates: total length, fitting count, minimum and
maximum size, and cumulative pressure drop where the source provided it.

The diff runs over the skeleton. The raw graph is retained so a reader can drill
into any collapsed run on demand, but it is never the unit of reporting.

## Consequences

- The overwhelming majority of churn disappears, because it lives inside
  collapsed runs. A reroute that preserves the connectivity of significant nodes
  becomes one edge-property change, which is what it actually is.
- The reports described in the README fall out of the skeleton naturally. Branch
  pressure drop is an edge attribute. Downstream airflow is a rollup over the
  subtree reachable through an edge. Reparenting is a change in which source root
  a node is reachable from. Orphaning is loss of reachability from any source.
- Identity matching gets dramatically easier and more reliable, because the
  elements that survive collapse are the ones with stable human-assigned marks.
  Matching thousands of anonymous elbows was never going to work; ADR-0003
  depends on this one.
- **A change entirely inside a collapsed run is only visible through its
  aggregates.** Replacing a long-radius elbow with a mitred one shows up as a
  pressure-drop delta on the edge, not as an elbow-level event. We accept this;
  it is the intended trade. Drill-down exists for when it is not enough.
- Significance is a judgement call, and therefore configurable. The default set
  above is a starting position, not a claim of correctness.
- Degree-based branch detection makes the skeleton sensitive to modelling
  artefacts — a tee split into two fittings may or may not read as one branch
  point. This needs real files to tune and is a known risk to revisit.

## Alternatives considered

**Diff the raw graph and filter the output.** Rejected: filtering after the fact
still requires computing and matching the full graph, keeps the cost, and gives
no place for run-level aggregates like cumulative pressure drop to live.

**Threshold on geometric movement.** Rejected as the primary mechanism. It
suppresses small moves but not regeneration, which is the dominant source of
churn, and it answers a geometric question when ours is a topological one.

**Diff only equipment and terminals, discarding the network.** Too lossy — it
cannot see reparenting or orphaning, which are the headline cases.
