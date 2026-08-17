## What and why

<!-- What changes, and what problem it solves. Link the issue or milestone. -->

## How to verify

<!-- The commands a reviewer runs, or the golden files to look at. -->

## Checklist

- [ ] `main` still works if this merges alone (no half-wired feature behind this PR)
- [ ] Tests added or updated; golden files regenerated deliberately, not blindly
- [ ] Output remains deterministic (sorted, no timestamps/paths/locale in payloads)
- [ ] A design decision here? An ADR is added or updated under `docs/adr/`
- [ ] No client or project model data committed (see CONTRIBUTING.md on fixtures)
