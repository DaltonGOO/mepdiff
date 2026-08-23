# ADR-0006: A two-tier format — canonical JSON, wrapped in a `.mepdiff` container

- **Status:** Proposed
- **Date:** 2026-08-23

## Context

[ADR-0004](0004-canonical-snapshot-representation.md) produced a format tuned for
one job: being committed and read in a pull request diff. It is indented rather
than minified, key-ordered, LF-terminated, and it prunes nulls specifically so
that the lines which changed are not buried. It rejected minified JSON outright,
on the grounds that these files are meant to be read.

[ADR-0005](0005-revit-as-the-first-adapter.md) gives the artefact a second job.
A modeller clicks Export, and the result goes into a project folder or an email
to a consultant. That path wants the opposite properties. Indented JSON for a
real air-side network runs to a line per node, per port, and per connection —
tens of megabytes for something that compresses by an order of magnitude — and
to a non-developer it looks like an unreadable wall of text with no indication
of what it is.

These are genuinely opposed requirements. One file cannot be both the thing git
diffs line by line and the thing a person emails. Trying to pick one loses
either the pull-request strategy that half of ADR-0004's justification rests on,
or the handover story that the tool exists for.

There is a third pressure. ADR-0002 promises drill-down into collapsed runs, and
that needs the raw pre-collapse graph to travel alongside the skeleton. A bare
JSON document has nowhere to put a second part.

## Decision

Two tiers, with an explicit hierarchy between them.

**Canonical JSON is normative.** It is what the JSON Schema describes, what
golden-file tests compare byte for byte, what is committed to a repository, and
what any conformance claim is made against. Nothing in this record changes a
byte of ADR-0004. The bare file is named `.mepdiff.json`.

**`.mepdiff` is an envelope, not a format.** It is a ZIP container that MUST
hold the byte-identical canonical JSON. It exists to make one small file for
transport and archive, and it adds no meaning of its own.

Layout:

```
manifest.json     container version, schema version, digest of the payload
snapshot.json     the canonical bytes from ADR-0004, unaltered
raw/              reserved: the pre-collapse graph for ADR-0002 drill-down
report/           reserved: rendered diff output
```

The reserved directories are specified now and built later. Reserving them is
the reason to define the envelope before there are files in the wild rather than
after.

**Both tiers are readable everywhere.** `mepdiff pack` and `mepdiff unpack`
convert between them, and every command that accepts a snapshot accepts either.
Reading a container unpacks it to bytes and then calls the existing `loads`;
there is exactly one parser, and the container path is never a second
implementation of it.

**The container is byte-reproducible too**, by the same discipline ADR-0004
applied to JSON: fixed entry order, a fixed constant timestamp rather than the
current time, a fixed compression level, and no extra fields. Zip determinism is
a known trap and gets a test of its own, alongside the existing LF-on-disk
assertion.

**A container is never the object of a golden test.** Golden tests compare the
payload. Reproducibility of the container is asserted directly and separately,
so that a change in a zip library cannot present as a change in a snapshot.

**The container version is distinct from the schema version**, and both appear
in the manifest. They change for different reasons and conflating them would
make one unversioned in practice.

## Consequences

- Handover becomes one small file that a modeller can email and a recipient can
  identify. Pull-request review keeps readable text. Neither job is compromised
  to serve the other.
- **Committing a `.mepdiff` container to a repository is a mistake**, because it
  is precisely the form that defeats what ADR-0004 was built for: GitHub renders
  it as "binary file changed" and the milestone-to-milestone diff disappears.
  The documentation must say `unpack` before committing, in those words.
- `.gitattributes` gains `*.mepdiff binary`, beside the existing `*.rvt` entry,
  so that git never attempts EOL translation on a zip.
- Two readable forms is two code paths and a class of bug where they disagree.
  The single-parser rule and the manifest digest are the controls; the digest
  turns a disagreement into an error rather than a wrong answer.
- **The manifest digest is not a signature.** It detects corruption and
  truncation, not tampering — anyone who edits the payload can recompute it. If a
  snapshot has to be evidence rather than a record, it needs a signature or a
  write-once store, and the manifest should leave room for the first. Claiming
  more than this for a digest would be exactly the kind of overstatement ADR-0003
  exists to prevent.
- A container makes size invisible, which removes the pressure that would
  otherwise tell us the JSON has grown unreasonable. Worth watching once real
  models arrive.

## Alternatives considered

**Make the container the only format.** One file, one story, no ambiguity about
which to use. Rejected: it kills the commit-per-milestone, read-the-diff-in-the-PR
strategy, which is half of ADR-0004's justification and the entire reason the
format is canonical in the first place.

**Bare JSON only, gzipped when it gets large.** The simplest thing that could
work, and `gzip` is universal. Rejected on three counts: `.json.gz` has nowhere
to put a manifest, nowhere to put the ADR-0002 drill-down graph, and no identity
of its own — nothing about the name tells a recipient what they have been sent.

**A binary or columnar payload — Parquet, SQLite, MessagePack.** Smaller and
faster to query. Rejected: it destroys human readability and text diff, which are
not incidental properties here but the ones ADR-0004 spent all of its effort
earning.

**Name the JSON now and build the container later, once a real model proves the
size hurts.** Reasonable, and correct if the exporter were not being written
right now. Rejected on timing: the envelope is far cheaper to define before
files exist in the wild than to retrofit around files that do, and the reserved
directories only work if they are reserved early.
