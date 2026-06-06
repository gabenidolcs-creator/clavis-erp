# Implementer isolation — reader/writer population separation

This is binding process gate **(1)** of the four clean-room gates: *the population that
**reads** premium/enterprise source must be separated from the population that **writes**
Bucket A reimplementations.* [Source: prd.md §8 line 472 item 1; item 4]

> **"Influenced by" counts as contamination — not just verbatim copying.** An implementer
> who has read the PE/EE source for a feature is contaminated for that feature even if
> they write entirely new code, because the license forbids work that is *influenced by*
> the protected source. Reconstructing from memory of the paid product is NOT clean-room.
> [Source: prd.md §8 line 471–472; architecture.md line 268]

## Chosen barrier

Record the selected isolation model in
[owner-and-sign-off.md §3](owner-and-sign-off.md). This document describes *how* the
barrier is enforced and *how a reviewer verifies an implementer's eligibility*.

### Mechanism: CODEOWNERS + branch protection (default for option (a))

`.github/CODEOWNERS` routes any change under `premium/` and `enterprise/` to the
clean-room owner, making PE/EE access visible and reviewable. Combine with the
repository branch-protection settings below.

**Branch-protection / access settings to configure (GitHub repo admin — manual, not
code):**

1. **Restrict who can touch PE/EE source.** Limit write/clone access to `premium/` and
   `enterprise/` to the *reader* population only (those allowed to maintain the paid
   product). Bucket A *writers* must not be in that group.
2. **Require the clean-room owner as a reviewer** (via CODEOWNERS) on any PR that touches
   `premium/` or `enterprise/`, so cross-population contact is always surfaced.
3. **Require the provenance gate status check** (`clean-room-provenance-gate`) to pass
   before merge on the protected branches (`develop`, `master`). See
   [merge-gate.md](merge-gate.md).
4. For option (b)/(c), document the contractor agreement / per-feature legal review path
   instead, and still keep gate (3).

> Repo-permission and branch-protection changes live in GitHub settings, not in this
> repository's files. CODEOWNERS and the CI gate are the parts enforceable *in-repo*;
> the access split must be applied by a repo admin and its completion recorded in
> [owner-and-sign-off.md](owner-and-sign-off.md).

## How a reviewer verifies eligibility

When reviewing a Bucket A PR, the reviewer confirms:

1. The PR's provenance record names the implementer and carries the implementer
   attestation (no PE/EE source read/used/recalled for this feature). See
   [templates/provenance-record-template.md](templates/provenance-record-template.md).
2. The implementer is in the writer population per the model recorded in
   [owner-and-sign-off.md §3](owner-and-sign-off.md) (walled-off group, contractor, or
   covered by per-feature legal review).
3. No `premium/` / `enterprise/` internal symbol appears in the behavior spec as the
   thing to replicate (free-core MIT symbols are allowed). See
   [allowed-sources.md](allowed-sources.md).

## References

- [Source: prd.md §8 line 472 items 1 & 4]
- [Source: architecture.md lines 205, 255, 268]
