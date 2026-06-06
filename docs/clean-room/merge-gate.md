# Clean-room provenance merge gate

This is binding process gate **(3)**: *a per-feature provenance record is a **hard merge
gate** for Bucket A pull requests — no provenance, no merge.* The gate is structural (CI
+ branch protection), not discipline. [Source: prd.md §8 line 472 item 3; architecture.md
lines 240, 425]

## What "Bucket A" means

A **Bucket A** PR is a clean-room reimplementation of a feature whose original code lives
under the Premium/Enterprise (PE/EE) license in `premium/`/`enterprise/`. The
reimplementation always lands in core `backend/src` / `web-frontend`, never in
`premium/`/`enterprise/`. [Source: architecture.md lines 205, 255]

## How a PR is flagged Bucket A

Either signal flips the gate on:

1. **Label** `bucket-a` on the PR, **or**
2. **PR-template checkbox** — the "This PR is Bucket A" box in
   `.github/PULL_REQUEST_TEMPLATE.md` is checked.

(Reviewers may additionally use a path heuristic — a PR adding core implementations of a
known premium feature should be labeled `bucket-a` — but the automated gate fires on the
label/checkbox so it never blocks ordinary PRs.)

## What the gate requires

When a PR is Bucket A, it must add or modify at least one provenance record under
`docs/clean-room/provenance/<slug>.md`, copied from
[templates/provenance-record-template.md](templates/provenance-record-template.md), that:

- has a `## Sources Consulted` section listing at least one source (all from the
  [allowed-source list](allowed-sources.md)),
- has a `## Implementer Attestation` section with the clean-room attestation checkbox
  **checked**, and
- does **not** cite any `premium/`/`enterprise/` path as a consulted source.

If any of those is missing, the gate fails and merge is blocked.

## Where the gate lives

| Piece | Path |
|---|---|
| Decision logic | [`scripts/check_provenance.py`](scripts/check_provenance.py) |
| Tests | [`scripts/test_check_provenance.py`](scripts/test_check_provenance.py) |
| CI workflow | [`.github/workflows/clean-room-provenance-gate.yml`](../../.github/workflows/clean-room-provenance-gate.yml) |
| PR checkbox | [`.github/PULL_REQUEST_TEMPLATE.md`](../../.github/PULL_REQUEST_TEMPLATE.md) |

## Required admin step (make it enforcing)

CI running is not enough to *block* merge — a repo admin must add the
**`clean-room-provenance-gate / provenance`** status check as a **required** check in
branch protection for `develop` and `master`. Until then the gate reports status but does
not hard-block. Record completion of this step in
[owner-and-sign-off.md](owner-and-sign-off.md).

## Running the gate locally

```bash
# Unit + end-to-end self-test
python3 docs/clean-room/scripts/test_check_provenance.py

# Simulate the gate for a change set
PR_LABELS="bucket-a" \
PR_BODY="" \
CHANGED_FILES="docs/clean-room/provenance/1-3-kanban.md" \
  python3 docs/clean-room/scripts/check_provenance.py
```

## References

- [Source: prd.md §8 line 472 item 3]
- [Source: architecture.md lines 240, 425, 437, 440]
