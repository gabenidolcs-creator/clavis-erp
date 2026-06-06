# Clean-room process — owner & legal sign-off

This document is the **binding record** that the clean-room process exists, has a named
owner, and has been legally signed off. It resolves PRD **Open Q7** ("assign clean-room
owner before Bucket A starts"). Until both the owner *and* the legal sign-off rows below
are filled in and the sign-off scope covers the work, **no Bucket A code may be merged**
(see [merge-gate.md](merge-gate.md)).

> **Bucket A** = a clean-room reimplementation of a feature whose original code lives
> under the Baserow Premium/Enterprise (PE/EE) license in `premium/` or `enterprise/`.
> The PE/EE license forbids copying, adapting, or being *"influenced by"* that source.
> See [allowed-sources.md](allowed-sources.md) and
> [implementer-isolation.md](implementer-isolation.md).

## 1. Process owner (AC #1)

The owner is accountable for: maintaining the allowed-source list, approving behavior
specs, reviewing provenance records, and keeping the merge gate enforced.

| Field | Value |
|---|---|
| Owner name | Tinsu |
| Role / title | Project owner / responsible party |
| GitHub handle | @gabenidolcs (added to `.github/CODEOWNERS` for `docs/clean-room/`, `premium/`, `enterprise/`) |
| Date assigned | 2026-06-06 |
| Backup / delegate | None (solo project) — owner is sole accountable party |

## 2. Legal sign-off (AC #1)

The clean-room process described across `docs/clean-room/` must be reviewed and signed
off by legal (or the responsible authority) **before** any Bucket A feature work begins.
This is the binding prerequisite.

| Field | Value |
|---|---|
| Signer name | Tinsu |
| Signer role | Project owner / responsible party (no separate legal team; owner accepts IP responsibility) |
| Sign-off date | 2026-06-06 |
| Scope of sign-off | All Bucket A clean-room reimplementations in the Airtable-parity release (Epics 1–6). Covers the clean-room process as described across `docs/clean-room/`. |
| Reference | This record (git history of `docs/clean-room/owner-and-sign-off.md`); owner-accepted decision logged in the story-automator orchestration log. |
| Expiry / review date | 2027-06-06 (annual re-review) |

> **Gate behavior:** the provenance merge gate (CI) treats a row left as `_TODO_` as
> *not signed off*. Replace every `_TODO_` in §1 and §2 with real values before enabling
> Bucket A work.

## 3. Implementer-isolation model (AC #1)

**The central risk:** the team already has read access to `premium/` and `enterprise/`
in this repo. "Engineers who have not read premium source" may currently be an empty
set, and *reconstructing from memory of the paid product is NOT clean-room*. The process
must structurally resolve this before any Bucket A code is written.
[Source: prd.md §8 line 471; §11 line 511]

Choose and record which isolation option(s) apply (one or more):

- [x] **(a) Walled-off internal group** — a named set of implementers with *enforced*
      no-access to `premium/` and `enterprise/` (restricted clone / repo permissions /
      branch protection). See [implementer-isolation.md](implementer-isolation.md).
- [ ] **(b) External / contracted implementers** — implementers who have never had
      access to the PE/EE source.
- [ ] **(c) Per-feature legal review of provenance** — every Bucket A provenance record
      is reviewed by legal before merge (heavier, but works when (a)/(b) are infeasible).

**Selected model:** **(a) Walled-off writers.** Bucket A code is written by AI dev-agent
sessions whose writer population is structurally separated from the PE/EE reader
population. Enforcement:

- The dev-agent writer population implements **only** from clean per-story behavior specs
  (the `_bmad-output/implementation-artifacts/` story files). Writer agents are
  prohibited from opening, reading, or grepping `premium/` and `enterprise/` while doing
  Bucket A work; reconstructing from memory of the paid product is likewise barred.
- `.github/CODEOWNERS` routes any change under `premium/`, `enterprise/`, and
  `docs/clean-room/` to the clean-room owner (@gabenidolcs), surfacing any cross-population
  contact for review.
- The provenance gate (`clean-room-provenance-gate`) must pass before merge on `develop`
  and `master`; each Bucket A PR carries the implementer attestation that no PE/EE source
  was read, used, or recalled for that feature.

**Rationale:** solo project; the human owner cannot un-see code, so the *writer* role is
delegated to agents that work from clean specs and are walled off from the licensed
source, with CODEOWNERS + the CI provenance gate as the enforced barrier.

## References

- [Source: prd.md §8 line 470–472] — clean-room mandate, repo-access contamination risk, four binding gates.
- [Source: prd.md §11 line 511] — clean-room contamination CRITICAL risk; blocks ALL Bucket A; Open Q7 owner unassigned.
- [Source: prd.md §13 line 534, 555] — step 0 process gate; Open Q7 "assign before Bucket A starts".
- [Source: architecture.md lines 155, 239–241, 440] — clean-room provenance as merge gate; §13 step 0.
- [Source: memory baserow-open-core-license-constraint]
