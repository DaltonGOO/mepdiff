# ADR-0004: A canonical, self-validating snapshot representation

- **Status:** Accepted
- **Date:** 2026-08-16

## Context

ADR-0001 established that the intermediate representation is the product and
that it doubles as an archival record: deterministic, ordered, text, committable
per milestone so any two points in a project's history can be diffed. That
promise only holds if the format is genuinely canonical. If two exports of an
unchanged model can differ by a byte, the golden-file test strategy collapses and
the archival record becomes untrustworthy at exactly the moment someone needs to
rely on it.

Several ordinary implementation choices quietly break that property. Iterating an
IFC file yields elements in file order, which varies between exports. Unit
conversion leaves residue in the low bits of a double. Negative zero is a
distinct IEEE-754 value that serialises differently from zero. Windows translates
`\n` to `\r\n` on write. None of these are exotic; all of them would have
produced spurious diffs.

There is a second, softer requirement. Adapters are where the messy work happens,
and the failure mode that matters is not a crash but a plausible-looking
snapshot with a dangling reference in it — something that surfaces three passes
later as an incoherent report.

## Decision

**Pydantic v2 models, frozen, with `extra="forbid"`.** Snapshots describe moments
that have already happened, so immutability is the honest model. Forbidding
unknown fields turns an adapter's typo into an error at the boundary rather than
a silently missing property in a report.

**SI base units throughout, always.** m3/s, Pa, m. Adapters convert on the way
in; reports convert on the way out; nothing in between carries a unit. This
costs raw-JSON readability — `0.188778` rather than `400` — and that is accepted,
because a mixed-unit archival format cannot be compared across snapshots without
knowing which exporter wrote each one.

**Quantisation to nine decimal places** on every stored quantity, with NaN and
infinity rejected outright and negative zero normalised. This is a canonicality
device, not a tolerance: it removes conversion residue while remaining far finer
than anything an engineer could observe. Deciding that two *different* airflows
are close enough to call unchanged is a reporting judgement that belongs to the
diff engine (M6), and conflating the two here would silently suppress real
changes.

**Canonical ordering enforced at construction**, not at serialisation:
collections sorted by identifier, mapping keys sorted, connection endpoints
sorted. Doing it in the model means every consumer sees canonical data, not just
the JSON writer.

**Referential integrity validated at construction.** A port must belong to a real
node; a connection must join real ports; system references must resolve. Two
connections describing the same join are rejected specifically because degree is
how M3 decides what a branch point is, so a duplicate corrupts the skeleton
rather than failing.

**Null and empty values pruned from the output**, losslessly, since every pruned
field has an empty default. A realistic snapshot would otherwise repeat
`"pressure_drop": null` across tens of thousands of elements and bury the lines
that actually changed.

**`None` means the source did not provide a value, and never means zero.**
ADR-0001 requires reporting absence honestly; this is where that becomes
mechanical.

**Explicit `UNKNOWN` members on every enum**, so an adapter meeting something it
does not recognise records that fact instead of guessing.

**Schema version with major/minor semantics.** Readers reject an unknown major
and accept an unknown minor.

## Consequences

- Byte-for-byte golden tests are viable, and the suite asserts the properties
  they depend on directly: repeated serialisation, construction-order
  independence, LF on disk, and round-trip losslessness.
- Adapter bugs surface at the adapter with a message naming the offending
  identifiers, capped at five so a broken adapter produces a usable traceback
  rather than a wall of text.
- Pydantic becomes a runtime dependency. Accepted: validation at the boundary is
  the point, and `model_json_schema()` publishes a schema so a snapshot archived
  today is checkable without this exact build.
- **`Source` carries no filename, timestamp, or user name** — only a digest. Each
  omitted field would make two exports of one model differ, and a file path would
  additionally leak a directory structure into a format meant to be committed to
  a public repository. The cost is that a snapshot cannot say what it was called.
- Synthetic identifiers (`mepdiff.model.ids`) are content-derived and therefore
  stable **within** a snapshot only. They are emphatically not matching keys —
  using one as such would report every edited element as a deletion plus an
  addition. The hashing scheme is pinned by a test, because changing it would
  invalidate every snapshot ever written.
- Property bags are flat scalars only. Nested structures would make ordering and
  diffing recursive problems, and neither IFC property sets nor Revit parameter
  lists need them.

## Alternatives considered

**Store values in source units with a unit tag.** More readable raw, and lossless
with respect to what the exporter said. Rejected: every consumer would then have
to convert before comparing, and the first one that forgets produces a diff
claiming a 2118× airflow change.

**Decimal instead of float.** Exact, and canonical by construction. Rejected as
disproportionate — quantised doubles are already finer than the measurements
they represent, and `Decimal` would spread through every downstream calculation
for no observable accuracy gain.

**Validate integrity in a separate pass.** Keeps the models simple. Rejected
because it makes validity optional in practice: any code path that skips the pass
gets an invalid snapshot, and the whole point is that an invalid one cannot
exist.

**Emit minified JSON.** Smaller. Rejected outright — these files are meant to be
read in pull request diffs, and minified JSON is one enormous changed line.

**Defer canonical ordering to the serialiser.** Simpler models. Rejected because
in-memory comparisons and hashing would then depend on construction order, so two
equal snapshots could compare unequal.
