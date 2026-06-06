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
| Owner name | _TODO: assign (engineering lead or named delegate)_ |
| Role / title | _TODO_ |
| GitHub handle | _TODO — also add to `.github/CODEOWNERS` for `docs/clean-room/`_ |
| Date assigned | _TODO (YYYY-MM-DD)_ |
| Backup / delegate | _TODO_ |

## 2. Legal sign-off (AC #1)

The clean-room process described across `docs/clean-room/` must be reviewed and signed
off by legal (or the responsible authority) **before** any Bucket A feature work begins.
This is the binding prerequisite.

| Field | Value |
|---|---|
| Signer name | _TODO_ |
| Signer role | _TODO (e.g. General Counsel / external IP counsel)_ |
| Sign-off date | _TODO (YYYY-MM-DD)_ |
| Scope of sign-off | _TODO — which buckets/features the sign-off covers_ |
| Reference | _TODO — link to signed memo / ticket / email of record_ |
| Expiry / review date | _TODO (re-review cadence)_ |

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

- [ ] **(a) Walled-off internal group** — a named set of implementers with *enforced*
      no-access to `premium/` and `enterprise/` (restricted clone / repo permissions /
      branch protection). See [implementer-isolation.md](implementer-isolation.md).
- [ ] **(b) External / contracted implementers** — implementers who have never had
      access to the PE/EE source.
- [ ] **(c) Per-feature legal review of provenance** — every Bucket A provenance record
      is reviewed by legal before merge (heavier, but works when (a)/(b) are infeasible).

**Selected model:** _TODO — record the choice and the rationale here._

## References

- [Source: prd.md §8 line 470–472] — clean-room mandate, repo-access contamination risk, four binding gates.
- [Source: prd.md §11 line 511] — clean-room contamination CRITICAL risk; blocks ALL Bucket A; Open Q7 owner unassigned.
- [Source: prd.md §13 line 534, 555] — step 0 process gate; Open Q7 "assign before Bucket A starts".
- [Source: architecture.md lines 155, 239–241, 440] — clean-room provenance as merge gate; §13 step 0.
- [Source: memory baserow-open-core-license-constraint]
