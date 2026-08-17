# Contributing to mepdiff

Design feedback from people who actually model MEP is worth more here than code,
especially early. If something in the change taxonomy would not survive contact
with a real coordination meeting, please open an issue and say so.

## Development setup

The Python ceiling is real: **IfcOpenShell 0.8.x declares `>=3.9,<3.13`**, and it
is the core dependency of the IFC adapter. Use 3.11 or 3.12.

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
```

On Windows, if `python` resolves to a newer interpreter, select 3.12 explicitly:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

Then:

```bash
ruff check . && ruff format --check .
mypy
pytest
```

CI runs exactly these, on Linux and Windows, against 3.11 and 3.12.

## Working agreements

**Every PR leaves `main` working.** Land features as a sequence of complete,
reviewable increments rather than one large branch. A PR that only makes sense
once a later PR merges is too big or split in the wrong place.

**Conventional Commits** for PR titles, since we squash-merge and the title
becomes the commit on `main`:

```
feat(ifc): read distribution ports and port connections
fix(match): stop matching terminals across different systems
chore: pin ruff to 0.6
docs(adr): record the skeleton-collapse decision
```

Scopes in use: `ifc`, `revit`, `model`, `skeleton`, `match`, `diff`, `analyse`,
`report`, `cli`, `ci`, `adr`.

**Design decisions get an ADR.** If a PR settles a question that a future
contributor would otherwise re-litigate — how identity is resolved, what counts
as a significant node, what severity means — add a record under `docs/adr/`
using [the template](docs/adr/0000-template.md). This project is mostly design
decisions; recording them is the point, not overhead.

## Two rules specific to this project

### 1. Output must be deterministic

Byte-for-byte, across runs, platforms, and Python versions. That means sorted
keys and stable collection ordering, no timestamps or absolute paths or locale
formatting inside payloads, and no reliance on dictionary insertion order derived
from file traversal.

This is not tidiness. The golden-file tests compare exact bytes, and a snapshot
that changes without the model changing is worthless as a handover record.

### 2. Never commit project models

This is a public repository. Real IFC and Revit files routinely contain client
names, addresses, project numbers, and personal information, and are usually
somebody else's intellectual property.

Test fixtures must be either:

- **synthetic** — built small and deliberately for the case under test, or
- **scrubbed** — reduced to the minimum subgraph that reproduces the behaviour,
  with project identity, addresses, author metadata, and file paths removed.

`.gitignore` refuses `*.ifc` and `*.rvt` outside `tests/fixtures/` as a
backstop, but the backstop is not the control. You are.

## Tests

Golden-file tests are the primary strategy: a fixture (or fixture pair) plus its
expected output, committed together. When behaviour changes intentionally,
regenerate the goldens and **read the resulting diff in the PR** — that diff is
the clearest description of what your change actually did, and reviewers will
read it as the specification.

Regenerating goldens without reading them defeats the entire test strategy.
