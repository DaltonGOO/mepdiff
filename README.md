# mepdiff

**A semantic diff for MEP system topology.**

Point it at two model snapshots and it tells you what changed about the *system*,
not what changed about the geometry:

```
Supply Air / AHU-1                                    3 significant changes

  ~ VAV-12          reparented    AHU-1 branch B  ->  AHU-2 branch A
                                  matched by GlobalId + Mark (confidence 0.98)
  ~ SA-TRUNK-02     downstream    4,200 -> 2,520 CFM  (-40%)
  ! DIFF-114        orphaned      no path to a supply source
```

> **Status: pre-alpha, and honest about it.** The repository is scaffolding plus
> design records right now — there is no working diff yet. The build order is in
> [Roadmap](#roadmap). Watch the repo if you want to see it land.

## Why

Geometric diffs and clash reports tell you that something moved. They do not tell
you that a terminal came off its trunk, that a branch is now carrying 40% less
air, or that somebody re-fed a VAV from a different air handler. Those are the
changes that matter at a design review or a model handover, and today they are
found by a person scrolling a schedule and hoping.

mepdiff is also aimed at a second problem: knowing exactly what was in a model
when you handed it over. Its snapshot format is deterministic, ordered, and
text — so you can commit one per milestone and diff any two points in a project's
history.

## How it works

The input format is an adapter concern. The project itself is the layer beneath:

```
adapters/   ifc -> IR              IFC2x3 / IFC4 via IfcOpenShell
            revit -> IR            a Revit add-in emitting the IR directly

core/       model                  normalised topology IR, deterministic on disk
            skeleton               collapse fitting/segment runs between
                                   significant nodes -- the noise control
            match                  tiered identity resolution, with reasons
            analyse                flow orientation, reachability, rollups
            diff                   change events with severity

report/     cli | json | markdown | github action
```

Two ideas carry the design, both recorded in [`docs/adr/`](docs/adr/):

**Collapse before diffing.** A raw graph diff of two duct models reports tens of
thousands of changes and is useless. mepdiff first reduces the network to a
skeleton whose nodes are only the significant elements — equipment, terminals,
dampers, branch points — with every intervening run of segments and fittings
collapsed to a single edge carrying aggregates. Branch pressure drop and
downstream airflow then fall out as edge properties.

**Show your work on identity.** IFC `GlobalId` is only mostly stable, and
fittings get regenerated constantly. Matching is tiered — stable ID, then
semantic key such as `Mark`, then structural scoring against already-matched
neighbours — and every match carries a confidence and a human-readable reason.
A diff you cannot audit is not useful for handover.

## Scope

v1 is **air-side only**: air handling equipment, duct networks, terminals, VAV
boxes. Hydronic, plumbing, and electrical are deliberately out of scope until the
core is proven.

## Roadmap

| | Milestone | Status |
|---|---|---|
| M0 | Repository scaffolding, CI, ADRs | in progress |
| M1 | Snapshot IR and determinism guarantees | |
| M2 | IFC adapter: elements, ports, connections, systems | |
| M3 | Graph construction and skeleton collapse | |
| M4 | Flow orientation, reachability, orphans, rollups | |
| M5 | Identity matching, tiers 0-1 | |
| M6 | Diff engine, change taxonomy, severity | |
| M7 | CLI and reports | |
| M8 | GitHub Action, self-dogfooding in CI | |
| M9 | Identity matching, tier 2 (structural) | |
| M10 | Revit exporter add-in | |

## Contributing

Design discussion is welcome and early feedback from people who model MEP is
especially welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) — and note the rule
about never committing project models.

## Licence

MIT. See [LICENSE](LICENSE).
