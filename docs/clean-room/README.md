# Clean-room process

Most of the Airtable-parity roadmap is **Bucket A** — clean-room reimplementations of
features whose original code lives under the Premium/Enterprise (PE/EE) license in
`premium/`/`enterprise/`. The PE/EE license forbids copying, adapting, or being
*"influenced by"* that source. This directory is the **process gate** (Epic 1, Story 1.1)
that must be satisfied **before any Bucket A code is merged**. [Source: prd.md §8, §11,
§13; architecture.md §13 step 0]

## The four binding gates

| # | Gate | Artifact |
|---|------|----------|
| 0 | Owner assigned + legal sign-off + implementer isolation chosen (Open Q7) | [owner-and-sign-off.md](owner-and-sign-off.md) |
| 1 | Reader/writer population separation ("influenced by" = contamination) | [implementer-isolation.md](implementer-isolation.md) · [`../../.github/CODEOWNERS`](../../.github/CODEOWNERS) |
| 2 | Behavior specs cite only allowed public sources | [allowed-sources.md](allowed-sources.md) · [behavior-spec template](templates/behavior-spec-template.md) |
| 3 | Per-feature provenance record = hard merge gate | [merge-gate.md](merge-gate.md) · [provenance template](templates/provenance-record-template.md) · [`scripts/`](scripts/) |

## For implementers of a Bucket A feature

1. Write a behavior spec from [allowed sources only](allowed-sources.md) using the
   [behavior-spec template](templates/behavior-spec-template.md).
2. Implement in core `backend/src` / `web-frontend` (**never** in `premium/`/`enterprise/`).
3. Add a [provenance record](templates/provenance-record-template.md) under
   `provenance/` and check the **Bucket A** box in the PR template.
4. The [provenance merge gate](merge-gate.md) blocks merge until a valid record is present.

## Status

This process is **not active** until §1 (owner) and §2 (legal sign-off) of
[owner-and-sign-off.md](owner-and-sign-off.md) are filled in. Until then, all Bucket A
work is blocked.
