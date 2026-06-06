# Security Review — Pass 2 (re-check of revised PRD)

**Scope:** Revised `prd.md` + `addendum.md`, re-checking the prior findings in `review-security.md` and hunting for NEW gaps introduced by the revision. Security/permission dimension only.

**Note on FR renumbering:** the revision renumbered several FRs. The prior review's FR-30 (field perms) is still FR-30; prior FR-31 (interface-only) is still FR-31; prior FR-33 (password share) is still FR-33. New FRs were inserted: **FR-14** (grouped-aggregate Data Source), **FR-29** (RBAC foundation, moved/renamed), **FR-33B** (export enforcement). The "Share principal" concept now has a Glossary entry (§3) and §10 backing. References below use the revised numbers.

---

**Overall verdict:** The four prior CRITICALs and the four prior HIGHs are substantively addressed in the revised text — every one is now CLOSED or PARTIAL, none remains fully OPEN — so §4.9 and the data-viz batches are **ready to enter the architecture/build phase, conditioned on the build sequence (§13 steps 1-2 first, step-7 gate) being honored and three residual PARTIAL items being nailed down in architecture.** This is a PRD-completeness verdict, not a code verdict.

---

## Prior-finding disposition

### Criticals

**C1 — Aggregation leak (charts/metrics) → CLOSED.**
FR-14 consequence: Data Source "Honors field-hide and row permissions of the requesting principal … does **not** aggregate over fields the principal cannot see." FR-30 explicitly names "chart/metric Data Sources (no aggregation, sum/min/max/labels)" and "Aggregations and formulas that transitively read a hidden Field are blocked or null-redacted … (no value inference via aggregate)." §11 carries a dedicated "Aggregation/formula inference leak" risk with an explicit-test mandate. Inference via min/max/small-bucket counts is named. Closed at PRD altitude.

**C2 — Share links / no permission principal → CLOSED.**
New Glossary "Share principal" (§3, "least-privilege identity … never the sharer's full permissions"). FR-17 resolves Data Sources "under a defined share principal … hidden-by-permission fields and restricted rows are NOT exposed." FR-33 ties password links to the same principal. §10 restates it cross-cuttingly. Closed.

**C3 — FR-33 weak password crypto → CLOSED.**
FR-33 now requires modern KDF (Argon2id/bcrypt, defined work factor), constant-time compare, high-entropy/unguessable token (no sequential IDs), rate-limit + lockout, and uniform error that "does not reveal whether a link exists." All five C3 sub-items present. Closed.

**C4 — Websocket broadcasts not per-recipient filtered → CLOSED (with one residual, see N1).**
§10 Security NFR: "websocket broadcasts filtered per recipient." FR-26 comments broadcast "only to recipients who can see that Row." FR-30 lists websocket broadcasts among enforced surfaces and requires "re-evaluate active sessions/websocket subscriptions" on permission change. SM-C1 was hardened to hold load constant so the added per-recipient filtering can't hide a latency regression. Closed; subscription-time authorization is implied but not crisply stated (N1).

### Highs

**H1 — Interface-only endpoint-scoped not data-scoped → CLOSED.**
FR-31 now denies "App Builder Data Source dispatch, formula evaluation, and websocket channels … beyond what the granted Page's elements expose," states "no back-door to the DB via a data source or formula," and "Data returned through a Page is the minimum the Page's Elements need — not the full row." Mandatory security review + role-combination matrix retained. Closed.

**H2 — No export FR → CLOSED.**
New **FR-33B** ("Exports honor Field Permissions") covers CSV/JSON/XLSX/Map/any download; hidden fields and restricted rows absent from every format; public/interface-only principals cannot export beyond granted surface. FR-30 cross-references it. §13 step 2 includes export enforcement. Closed.

**H3 — @mention leak → CLOSED.**
FR-26: "@mention is only allowed for members who already have access to the Row; mentioning a member without Row access is rejected (no notification, no row link leak)"; comments "must not embed or leak hidden-by-permission Field values to lower-privileged subscribers." FR-27: notification fires "only if the recipient can access the Row." Mentionable-set is bounded to Workspace members but row-access-gated, which covers the leak. Closed. (Mentionable-set scope vs base membership left slightly loose — minor, folded into N4.)

**H4 — Role-interaction matrix unenumerated → PARTIAL.**
§11 now *describes the axes* of the matrix: "{Viewer, Commenter, Editor, Admin, interface-only} × {field-permission state} × {personal/locked view} × {public/password share} with defined precedence rules," and §13 step 7 gates release on it. This is a real improvement over "asserted, not specified." But the PRD still **does not contain the resolved-cell table or the precedence rule itself** (e.g., "most-restrictive-wins"). The prior finding asked for the matrix as a deliverable; the PRD now commits to producing/testing it but defers the content to the security gate. Acceptable for a PRD, but the precedence rule should be stated as a one-liner now since FR-30/FR-32 interactions depend on it. PARTIAL.

---

## Disposition of prior MEDIUM/LOW (carried items)

- **M1 (geocoded PII inherits field perms) → CLOSED.** §11 geocoding risk: "geocoded lat/lng treated as derived data under the source Field's permissions"; §8 Privacy reinforces. FR-33B covers Map export.
- **M2 (personal-view IDOR) → CLOSED.** FR-28: "direct fetch of another member's Personal View by ID returns 403 (not just list-hiding — no IDOR)." Addendum p38 mirrors.
- **M3 (cache/session invalidation on perm change) → CLOSED.** FR-30: "a permission change invalidates any cached row/field payloads and re-evaluates active sessions/websocket subscriptions"; §10 restates.
- **M4 (no security gate on Batches 2-4 / sequencing) → CLOSED.** Major structural fix: §13 moves RBAC to step 1 and the permission-enforcement layer to step 2 (**before** views/dashboard/app-builder), with a step-7 release-blocking security gate. The "permission-aware data source" is now FR-14, sequenced ahead of charts.
- **L1 (lock/unlock authority) → CLOSED.** FR-32: "Lock can be removed only by an Admin or the lock owner."
- **L2 (comment moderation) → CLOSED.** FR-26: "admins can moderate others' Comments."
- **L3 (threat model artifact) → CLOSED.** §11 + §13 step 7 require "threat model + role-combination test matrix + security review" as a release gate.
- **L4 (embed-write privilege escalation) → CLOSED (as a flagged decision).** Open Q6 re-tagged "Now security-load-bearing — interactive embeds are a privilege-escalation surface (must honor FR-30/Role)"; FR-24 consequence: "Read/interaction permissions follow the viewer's Role." Decision still open but correctly framed as security-load-bearing.

---

## NEW / residual findings (introduced or surfaced by the revision)

### N1 — Websocket *subscription-time* authorization not explicitly required (HIGH→MEDIUM)
The revision filters broadcast *payloads* per recipient (good), but the prior C4 fix also called for **authorizing channel subscription at subscribe time**. The revised PRD only states payloads are filtered and subscriptions are "re-evaluated" on permission change. An interface-only collaborator or Commenter could still *subscribe* to an underlying table's realtime channel; if any future event-type forgets per-recipient redaction, the channel membership itself is the leak. FR-31 denies "websocket channels … beyond what the granted Page exposes" for interface-only, which helps, but the general RBAC roles (Viewer/Commenter on a table with a hidden field) have no stated subscribe-time check.
**Fix:** Add to §10/FR-30: "Channel subscription is authorized at subscribe time against the recipient's Role; a member may not subscribe to a row/table channel it cannot read." Defense-in-depth behind payload filtering.

### N2 — Search/filter as an inference oracle is named for *read* but not for *filtering on a hidden field* (MEDIUM)
FR-30 lists "search/filter results" as a surface where a hidden field must not be returned. But it does not address using a **hidden field as a filter/sort predicate**: an unauthorized member who can construct a view filter `Salary > 100000` and observe which rows appear/disappear (or the result count) infers the hidden value without it ever being returned. Same oracle exists for sort order on a hidden field. This is the filter-side analogue of the aggregation leak (C1) and is not explicitly blocked.
**Fix:** FR-30 consequence: "A field the principal cannot see may not be used as a filter, sort, group, or search predicate (rejected/ignored server-side); result membership and counts must not vary based on a hidden field's value for unauthorized principals." Add a regression test (count/membership stability).

### N3 — Formula/lookup/rollup transitive reads: "blocked or null-redacted" leaves a leaky branch unspecified (MEDIUM)
FR-30 says transitive reads are "blocked or null-redacted for unauthorized principals." The **null-redact** branch is itself an inference channel for some formulas: e.g., a boolean formula `IF(Salary > X, "high", "low")` redacted to null tells the viewer nothing, but a pre-existing stored/computed formula field whose *result* depends on a hidden input and is itself visible (not hidden) leaks a derivation of the hidden field. The PRD blocks formulas that "reference" a hidden field but does not say a **visible formula/lookup/rollup field whose inputs include a hidden field must itself become restricted (or recompute as null) per principal.** Cross-table lookups/rollups pulling a field hidden in the *source* table are the highest-risk path and aren't called out distinctly from same-table formulas.
**Fix:** State the propagation rule explicitly: "A formula/lookup/rollup field that transitively reads a field the principal cannot see is itself treated as hidden-by-permission for that principal (not merely the raw field)." Call out cross-table lookup/rollup as a named test case.

### N4 — Dashboard *public* share (FR-17) vs *password* share (FR-33) principal equivalence is asserted but the anonymous principal's field-permission resolution is undefined (MEDIUM)
Both FR-17 and FR-33 resolve under "the share principal," but the PRD never defines **how field permissions resolve for an identity that is not a workspace member** (the anonymous/least-privilege principal). FR-30 keys visibility off "Role/member"; the share principal is neither. Two un-pinned questions: (a) does the public principal default to *deny-all fields except those explicitly view-shared*, or *allow-all-not-explicitly-hidden* (the dangerous default the prior C2 warned about)? (b) Is the password-share principal identical to the no-password public principal, or does a password upgrade visibility? The revision fixed "which sharer's perms" but not "what the anonymous principal can see by default."
**Fix:** Define the public/share principal as **deny-by-default**: it sees only fields/rows explicitly included in the shared View/Dashboard config, never inheriting "not-yet-restricted" fields. State that password presence does not change the field set (auth gate only, same principal).

### N5 — Geocoding cache is shared/global but field permission is per-principal (LOW)
M1 was closed at the visibility layer (lat/lng inherits the source field's permission). But FR-13 caches coordinates "and not re-requested on every load," and the addendum caches server-side. The cache is a single derived value per row; the permission check must happen at **read/serialization time per principal**, not at cache-write time, or a principal who can't see the address still reads the cached pin. The PRD implies this (M1 fix) but the cache-key/where-enforced detail belongs in architecture.
**Fix (architecture note):** Geocode cache is permission-agnostic storage; enforce the source-field permission at Map-view/export serialization per principal, identical to any other derived field. Add to addendum Map note.

### N6 — Permission-change cache invalidation scope vs the geocode/aggregate caches (LOW)
FR-30/M3 invalidate "cached row/field payloads" on permission change, and FR-15 charts cache/refresh. The revision does not state that **chart/dashboard aggregate caches and the Redis model-cache** are in the invalidation set when a *field permission* (not row data) changes — only "row/field payloads." A stale cached aggregate computed before a field was restricted could still be served via a dashboard until its own refresh interval.
**Fix:** Make M3's invalidation explicitly include aggregate/chart caches and the Redis model-cache, not just row-detail payloads.

---

## Summary

- Prior findings: **C1 CLOSED, C2 CLOSED, C3 CLOSED, C4 CLOSED; H1 CLOSED, H2 CLOSED, H3 CLOSED, H4 PARTIAL; M1-M4 CLOSED; L1-L4 CLOSED.** → 15 CLOSED, 1 PARTIAL, 0 OPEN.
- New findings: **N1 (MED, ws subscribe-time authz), N2 (MED, filter/sort inference oracle), N3 (MED, formula/lookup/rollup propagation rule), N4 (MED, anonymous share-principal default field resolution), N5 (LOW, geocode cache per-principal enforcement), N6 (LOW, aggregate/Redis cache invalidation on perm change).**
- None of the new findings is a blocker for entering architecture; N2/N3/N4 should be resolved in the architecture phase before the §13 step-2 permission layer is coded, and H4's precedence rule should be stated now.
