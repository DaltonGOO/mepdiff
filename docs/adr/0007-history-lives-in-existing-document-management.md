# ADR-0007: History lives in the project's existing document management

- **Status:** Proposed
- **Date:** 2026-08-23

## Context

[ADR-0001](0001-normalised-ir-with-ifc-as-first-adapter.md) set a second goal
beside the diff: knowing exactly what was in a model when it was handed over, and
being able to diff any two points in a project's history. ADR-0004 built the
format that makes it possible. Nothing yet says where the files go.

Git answers this completely — for a developer. It versions, diffs, attributes,
reviews, and backs up, at no cost and with no server. It is the right answer for
this repository's own fixtures and it will stay that way.

It is the wrong answer for the audience. [ADR-0005](0005-revit-as-the-first-adapter.md)
moved the project toward MEP modellers, and a mechanical designer is not going to
run `git commit`. A history mechanism that only developers can operate reproduces
exactly the gap ADR-0005 was written to close.

The obvious next move is a hosted service: blob storage, a database, an ingest
endpoint, accounts. It is attractive, it is the direction this kind of tool
usually goes, and it is wrong for now — for reasons of sequence rather than
design.

The forces against it are concrete. There is no diff engine yet, so there are no
change events for a database to index; a database standing in front of a product
that does not exist is infrastructure built on speculation. Holding customers'
MEP snapshots makes this project a data processor, with the contracts, retention
policy, and data-residency obligations that implies — a serious undertaking for
something at pre-alpha, and one CONTRIBUTING's rule about project models shows
the project already takes seriously. And a hosted service forces a licensing
decision that has not been made: this repository is MIT, and an
open-engine-plus-hosted-service split should be chosen deliberately rather than
arrived at.

Set against all of that, the audience already has cloud storage. AEC firms run
ACC or BIM 360 Docs, or SharePoint, or a network drive with a backup policy. That
storage already carries the firm's access control, retention rules, data
residency, and disaster recovery, all of them already approved by whoever
approves such things.

## Decision

**mepdiff writes files. Where they live is the project's business.**

The blessed pattern is a folder in whatever the firm already uses — ACC / BIM 360
Docs, SharePoint, or a network drive — holding one `.mepdiff` per milestone. The
tool inherits that storage's access control, retention, residency, and backup by
having no opinion about any of them.

**mepdiff makes no network call.** This is stated as a property of the tool, not
merely as an unbuilt feature. A utility that reads client models and transmits
nothing is a materially easier thing for a firm's IT to approve than one that
does, and that difference matters more to adoption than any feature a service
would add.

**No hosted service, no database, no accounts.**

Two mechanisms make a folder work as history rather than as a pile:

- **Filenames carry the ordering a human reads.** The documentation recommends a
  convention; it does not enforce one, because file naming is a firm's convention
  and not this tool's to dictate.
- **`Source.digest` identifies a payload independently of its filename.** ADR-0004
  put it there for provenance, and it does double duty here: a renamed, copied,
  or re-downloaded file is still identifiable as the same snapshot. That is the
  substitute for a database key, and it is the reason a folder does not degrade
  into ambiguity the first time someone appends `_FINAL_v2`.

**Nothing here forecloses a service.** Content-addressed files in a folder are
precisely what a future ingest would consume — this is a deferral with the
migration path left open, not a refusal.

## Consequences

- Zero infrastructure, zero hosting bill, no on-call, and no data-processor
  relationship with anyone's client data. At this stage that is the difference
  between shipping and not shipping.
- The MIT licensing question stays closed. There is no service to license
  differently and no split to design.
- **Cross-project query is given up.** "Every VAV reparented across all jobs this
  quarter" is a database question and a folder cannot answer it. Accepted
  willingly: nobody has asked, and there is no diff engine to generate the events
  that would be queried.
- **Automatic capture is given up.** Snapshots happen when a person clicks, not
  on every central-model sync. This is a smaller loss than it appears — the
  archival goal in ADR-0001 is about milestones and handovers, which are human
  events anyway, and a snapshot per sync would bury the ones that matter.
- **A folder offers no integrity guarantee.** It can be edited, and it can be
  deleted. The digest detects a changed payload; nothing prevents a file
  disappearing. If a snapshot needs to stand up in a dispute it needs a write-once
  store or a git commit, and the documentation must say so plainly rather than
  letting a folder imply a permanence it does not have.
- **Discovery is by filename**, so a firm with no naming discipline gets a mess,
  and the recommended convention is documentation rather than enforcement. This
  is a real limitation and the most likely source of "the tool did not help"
  feedback.
- **Revisit trigger.** This record should be reopened when either (a) someone
  asks a question a folder genuinely cannot answer, or (b) the diff engine exists
  and its change events are worth accumulating across projects. Naming the
  trigger is what makes this a deferral rather than a position.

## Alternatives considered

**Azure Blob Storage plus a PostgreSQL index, with files still canonical.** The
strongest hosted design available: canonical bytes live in content-addressed blob
storage as the source of truth, Postgres indexes only metadata and extracted
change events, the database is rebuildable from the blobs at any time, and Entra
ID handles authentication — which fits an audience already on Microsoft 365.
Rejected on timing rather than merit. There is no diff engine, so there are
no change events to index, and the whole structure would be built before the
thing it indexes exists. **This is the design to return to** when the revisit
trigger fires.

**PostgreSQL as the store of record, snapshots normalised into tables.** Queryable
and relational. Rejected because it demotes the file format from source of truth
to export, which is exactly the property ADR-0004 spent its entire effort
earning. A snapshot that only exists as rows is not an archival record.

**Git as the recommended history for everyone.** Free, excellent, already in use
here. Rejected as a recommendation to users for the reason in the context: it is
the right answer for this repository and the wrong one for the audience.

**A bundled local database — SQLite — as a snapshot index.** Would give fast local
query with no server. Rejected for now: it is a cache with nothing behind it that
the folder does not already provide, and it introduces a state file that can fall
out of agreement with the folder it describes, which is a class of bug with no
compensating benefit at this size.
