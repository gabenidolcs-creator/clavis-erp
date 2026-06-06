# Security Review — Permission / Access-Control Completeness

**Scope:** PRD `prd.md` + `addendum.md` for the Clavis ERP Airtable Parity Release, evaluated **only** on the security/permission dimension. Focus: §4.9 roles/permissions (FR-26..FR-33) and every new data-surfacing path (Map, Dashboard, App Builder charts/metrics/embeds, exports, websockets) that could leak a hidden-by-permission field (FR-30) or restricted rows.

**Verdict:** The PRD names server-side enforcement as a principle (§10 Security NFR, §11) but does **not** specify enforcement at every surface. Multiple new read paths (charts, metrics, dashboard share links, websocket broadcasts, exports, geocoding) bypass the field/row permission layer in the most likely implementations, and the highest-risk feature (FR-33 password share) is under-specified to the point of being insecure-by-default. Treat as **NOT READY to build §4.9 / data-surfacing FRs** until the findings below are addressed.

---

## CRITICAL

### C1 — Field permission (FR-30) enforcement is not guaranteed at the aggregation layer (charts/metrics)
**§:** §4.6 FR-15/FR-16, §4.8 FR-22/FR-23, §4.9 FR-30
**Problem:** FR-30 says a hidden-by-permission field "is not returned by the API... and does not render in any View, embed, or export." Charts and metrics do **not** return raw field values — they return *aggregates* (sum/avg/min/max/count, and category labels). A "Total Salary by Department" metric or a bar chart whose category axis is a restricted single-select leaks the protected field's contents (or a close derivation) without ever "returning the field." The PRD's enforcement language is row/field-value-shaped and silent on aggregation. The addendum routes all charts/metrics "via service registry" with no statement that the service layer filters its selectable/groupable field set by the requester's field permissions.
**Fix:** Add an explicit FR consequence: "Chart/metric Data Sources MUST NOT allow a field the requester cannot see (FR-30) to be used as a value, category, series, or filter dimension; the service layer rejects (403) or omits restricted fields before aggregation, enforced server-side." Require an aggregation-leakage test (e.g., min/max over a hidden numeric field reveals exact values; small-bucket category counts reveal membership).

### C2 — Public / password share links (FR-17, FR-33) bypass the per-member permission model entirely
**§:** §4.6 FR-17, §4.9 FR-30/FR-33
**Problem:** A shared Dashboard/View/App Page renders "read-only without authentication" (FR-17). There is **no authenticated member**, so per-member/per-role field permissions (FR-30) and personal/locked-view scoping have no subject to evaluate against. The PRD never defines *which* permission identity an anonymous (or password-only) viewer assumes, nor that hidden-by-permission fields and restricted rows are stripped from shared/public payloads. Default behavior of "share the view as the sharer sees it" would publish admin-only fields to the anonymous internet.
**Fix:** Specify the effective permission principal for every share surface: a public/password link MUST resolve to a **least-privilege snapshot** (e.g., a "public viewer" pseudo-role) and MUST strip every field hidden-by-permission for that principal and every row excluded by view/row filters — server-side, before serialization. Add a consequence to FR-17 and FR-33 and a test that an admin-only field never appears via a public link.

### C3 — FR-33 password share: hashing scheme, rate-limiting, and link enumeration unspecified
**§:** §4.9 FR-33, §10 Security NFR
**Problem:** FR-33 says only "password is stored hashed." That is insufficient for a security-sensitive feature:
- No algorithm/work-factor named — a fast hash (MD5/SHA-256) on a user-chosen share password is brute-forceable offline if the token+hash ever leak.
- **No rate-limiting / lockout** on the password-prompt endpoint — online brute force of typically-weak share passwords is wide open.
- **No constant-time comparison** requirement (timing oracle).
- Share-link **slug enumeration**: nothing specifies high-entropy, unguessable tokens; sequential or short slugs let attackers enumerate password-protected links and then brute the password.
- No statement on whether a wrong password reveals existence of the resource (information disclosure).
**Fix:** Require: (a) slow KDF (Argon2id or bcrypt/PBKDF2 at agreed work factor) via Django's password hashers; (b) per-link + per-IP rate limiting and exponential backoff/lockout on the verify endpoint; (c) constant-time verification; (d) ≥128-bit random unguessable share tokens; (e) uniform response for "link doesn't exist" vs "wrong password." Add these as testable consequences and a threat-model callout.

### C4 — Websocket broadcasts not specified to respect per-field / per-row permissions
**§:** §4.1 FR-2, §4.2 FR-5, §4.3 FR-7, §4.6 FR-15, §4.9 FR-26/FR-30, §10 Real-time NFR
**Problem:** Many FRs broadcast row mutations in real time (Kanban drag, Calendar/Timeline/Gantt moves, comments, "live-push to charts" in FR-15). The §10 Real-time NFR and SM-C1 optimize for latency and say broadcasts go "over the existing WebSocket layer" — but **nothing requires the broadcast payload to be filtered per recipient**. A row-updated event that includes a hidden-by-permission field's value (FR-30), or a comment broadcast on a row the recipient can't see, leaks data to every subscribed client regardless of role. This is the classic "enforced at REST, leaked at WS" gap, and it directly collides with FR-30's "across all View Types and embeds" promise. Interface-only collaborators (FR-31) and Commenters subscribed to a board channel are the most exposed.
**Fix:** Add an NFR/consequence: "Real-time broadcasts MUST apply the same field-visibility and row-access filtering as the REST serializer, per recipient/channel; no broadcast may include a field or row the recipient is not authorized to see. Channel subscription is authorized at subscribe time against the recipient's role." Require a test: a member without access to a hidden field receives a redacted row-update event.

---

## HIGH

### H1 — Interface-only collaborator (FR-31): data-source / formula / websocket back-doors not enumerated
**§:** §4.9 FR-31, §4.8 FR-22/FR-23/FR-24, addendum p38
**Problem:** FR-31 blocks "all Database/Table/View endpoints (403)" and hides DB nav — but an interface-only collaborator's entire purpose is to view App Pages whose **chart/metric/embed Elements pull from those same tables via the service registry**. The lockdown is endpoint-scoped, not data-scoped. Open back-doors not addressed:
- **Data-source endpoints**: the App Builder data-source dispatch/query endpoints are distinct from the DatabaseApplication endpoints FR-31 blocks; if those aren't equally clamped to the page's published config, the collaborator can re-parameterize a chart/embed query to pull other fields/tables.
- **Formulas**: runtime formulas / page parameters that reference table data can dereference rows or fields outside the intended scope (a formula leaking DB access — explicitly called out in the task).
- **Websocket channels**: can an interface-only collaborator subscribe to the underlying table's realtime channel even though the REST endpoint 403s? (See C4.)
- **Row detail/comment endpoints** opened from an embed (FR-24, UJ-3 has Priya opening a record and commenting) — are those serviced by the blocked Database endpoints or a separate App-scoped path? Ambiguous.
**Fix:** Replace "all Database/Table/View endpoints return 403" with an allow-list model: enumerate every endpoint class an interface-only collaborator may reach (published-page render, scoped data-source dispatch bound to that page's saved config, scoped row-detail/comment for rows the page exposes) and require all others — including data-source query mutation, formula evaluation against arbitrary fields, and raw table websocket channels — to 403/redact. Mandate the "exhaustive role-combination tests" promised in §11 actually cover these paths.

### H2 — Exports are named as a leak surface but no export FR enforces FR-30
**§:** §4.9 FR-30, §6 (no export FR)
**Problem:** FR-30 promises hidden fields don't render "in any... export," yet there is **no export functionality FR** in this release and no statement that existing CSV/JSON/XLSX export paths (which Baserow already has) are updated to honor the new field permissions and personal/locked-view scoping. New views (Kanban/Calendar/Gantt/Map) and dashboards typically grow their own export/print/"download" affordances; each is a fresh serialization path that can bypass field permissions. Map view in particular exports geocoded address/lat-lng (PII).
**Fix:** Add a cross-cutting consequence: "All existing and new export/download/print paths MUST apply field-permission and row-access filtering identically to the API (FR-30); add regression tests for each export format that a hidden-by-permission field is absent." Explicitly list export among the surfaces requiring security sign-off.

### H3 — Comment @mention can leak row data and notify users who lack row/field access
**§:** §4.9 FR-26/FR-27, §2.3 UJ-3
**Problem:** Two distinct leaks, neither addressed:
1. **@mention notification leak**: FR-27 notification "links to the Row/Comment." If a Commenter @mentions a member who does **not** have access to that row (or to a hidden field referenced in the comment body), the notification + linked comment can surface row content the recipient shouldn't see. There is no check that the mention target has access to the row.
2. **Comment body as exfil channel**: a Commenter who can *see* a hidden-by-permission field's value in a comment (or who pastes restricted data) can broadcast it via comment to lower-privileged subscribers (ties to C4). Also, can a Commenter @mention/notify *any* workspace member, including those outside the base — an enumeration/spam/notification-abuse vector?
**Fix:** Specify: (a) @mention targets are restricted to members who already have at least view access to the row/table; mentioning others is rejected or the notification is access-checked at send and at render; (b) comment read/broadcast respects row access (a Commenter cannot comment on a row they can't see); (c) define who is mentionable (workspace members with base access only). Add tests.

### H4 — Role interaction matrix (Commenter × field-perms × personal/locked views) is asserted, not specified
**§:** §4.9 FR-28..FR-32, §11
**Problem:** §11 promises an "exhaustive role-combination test matrix" but the PRD never enumerates the interactions, leaving ambiguous (and likely under-implemented) cases:
- **Commenter + field permission**: can a Commenter see a field that is edit-restricted-but-visible vs hidden-by-permission? Does commenting on a row expose hidden fields in the row-detail panel?
- **Commenter + personal view**: can a Commenter create a Personal View? FR-28 says "a member can mark a View as Personal" — does that include Commenter/Viewer, and does a personal view let a low-role user bypass a locked-view restriction by cloning?
- **Personal view + field permission**: does a personal view re-expose a hidden field if the owner had it visible before the restriction was applied?
- **Locked view + field permission + Commenter**: FR-32 says data is "still editable per the member's Role" — confirm a locked view cannot be used to widen field visibility.
- **Interface-only + Commenter**: can an interface-only collaborator hold Commenter rights on embedded rows (UJ-3 implies yes) — what's the combined surface?
**Fix:** Add an explicit role × capability × field-permission-state matrix (table) to §4.9 or the addendum defining the resolved permission for each cell, and make the §11 test matrix trace to it. Resolve precedence rules (most-restrictive-wins) explicitly.

---

## MEDIUM

### M1 — Map geocoding sends restricted-field PII to third party without permission gating
**§:** §4.5 FR-12/FR-13, §8 Privacy
**Problem:** §8 covers third-party egress for addresses generally, but not the permission interaction: if the address field becomes hidden-by-permission (FR-30), is geocoding still triggered, and is the cached lat/lng (derived from a now-restricted field) exposed in the Map view or via share/export to users who can't see the address? Derived coordinates are a re-identification of the protected address.
**Fix:** State that geocoding cache entries inherit the source field's permission/visibility; coordinates derived from a hidden field are not surfaced to unauthorized viewers or public links. Add to §8 and FR-13.

### M2 — Personal View (FR-28) ownership/listing enforcement is server-side-unconfirmed for non-list paths
**§:** §4.9 FR-28, addendum p35
**Problem:** Addendum says personal views "filter by current user in listing; check in ViewHandler." Filtering the *list* is not the same as authorizing *direct access by view ID* (IDOR). Nothing states that fetching/loading a personal view by ID, or its data endpoint, 403s for non-owners — only that it's "hidden from the View list." A guessable/sequential view ID would let another member load a teammate's personal view directly.
**Fix:** Add consequence: "A Personal View's read/data/config endpoints return 403 for non-owners, not merely omit it from listings." Test direct-ID access by a non-owner.

### M3 — "Hide-by-permission" only on add/edit timing; field-visibility change must purge caches/active sessions
**§:** §4.9 FR-30, §4.6 FR-15 (Redis model-cache, addendum p13)
**Problem:** The addendum notes "Redis model-cache invalidation come free if patterns followed" and dashboards cache/refresh. When an admin *newly restricts* a field, cached chart/metric/dashboard payloads, already-open websocket sessions, and rendered embeds may continue serving the now-hidden field until refresh. No FR requires invalidating caches/sessions on permission change.
**Fix:** Add consequence: "Changing a field permission or role invalidates relevant server/Redis caches and forces re-authorization of active websocket subscriptions so the change takes effect without requiring the victim to reload." Test that a restriction takes effect on in-flight sessions.

### M4 — No security-review gate defined for the data-surfacing batches (only FR-31)
**§:** §11, §13
**Problem:** §11 mandates security review "esp. FR-31," but the leak surfaces in C1/C2/C4/H1/H2 live in Batches 2–4 (Dashboard, App Builder) which ship *before* the collaboration batch in the build sequence (§13). Those batches have no security-review gate, yet they create the very read paths that FR-30 must later constrain. Sequencing field permissions last (Batch 5) means charts/embeds/share links are built with no permission model to test against.
**Fix:** Add a security-review gate to Batches 2–4 covering data-source/aggregation/share/export/websocket leak paths, OR move the field-permission + share-link enforcement primitives earlier so later read surfaces are built permission-aware. Add an explicit "permission-aware data source" foundational item to §13 step 1.

---

## LOW

### L1 — Locked View (FR-32) lock-removal authority underspecified
**§:** §4.9 FR-32
**Problem:** "Lock can be removed by an authorized member" — "authorized" is undefined. If any Editor can unlock, locking is cosmetic against the contractor threat in UJ-4.
**Fix:** Define who may lock/unlock (e.g., view owner or admin only); 403 otherwise.

### L2 — Comment edit/delete authorization scope ambiguous
**§:** §4.9 FR-26
**Problem:** "Editing/deleting one's own Comment is supported per permission" — does an admin/row-owner have moderation delete rights? Can a Commenter delete others' comments? Undefined.
**Fix:** Specify ownership-based edit/delete + admin moderation override, enforced server-side.

### L3 — No threat-model artifact referenced
**§:** §11, addendum
**Problem:** §11 lists permission regression as a risk but no threat model / data-flow diagram is required as a deliverable for the new read surfaces. Run Script (deferred) gets a "security audit mandatory" note (addendum p49); the shipping permission features deserve the same rigor.
**Fix:** Require a lightweight threat model (STRIDE or data-flow) covering every new read path before Batch 5 ships, as an architecture-phase deliverable.

### L4 — App Builder embed interactivity (Open Q6) has a permission consequence, not just UX
**§:** §4.8 FR-24, §14 Q6
**Problem:** Open Q6 treats "embeds interactive vs read-only" as UX, but if drag-edit is allowed via an embed, an interface-only collaborator gains *write* access to the underlying table through the App layer — a privilege-escalation path. The decision is security-load-bearing.
**Fix:** Re-tag Q6 as security-relevant; if interactive, specify that writes via embed are authorized against the viewer's data-layer role (not just page access), and that interface-only collaborators cannot write unless explicitly granted.

---

## Summary of required additions (checklist for PRD authors)
- [ ] Aggregation-layer field-permission enforcement for charts/metrics (C1)
- [ ] Least-privilege principal + field/row stripping for all public/password share payloads (C2)
- [ ] KDF, rate-limit, constant-time, high-entropy token, uniform-error for FR-33 (C3)
- [ ] Per-recipient field/row filtering on all websocket broadcasts + authorized subscription (C4)
- [ ] Allow-list lockdown for interface-only (data-source dispatch, formulas, WS channels, row/comment endpoints) (H1)
- [ ] Export/download/print paths honor FR-30 + add export FR/regression tests (H2)
- [ ] @mention access-check + comment row-access enforcement + mentionable-set definition (H3)
- [ ] Explicit role × field-permission-state interaction matrix with precedence rules (H4)
- [ ] Geocoding cache inherits field permission (M1)
- [ ] Personal-view direct-ID 403, not list-only hiding (M2)
- [ ] Cache/session invalidation on permission change (M3)
- [ ] Security-review gate on Batches 2–4; permission-aware data source in §13 step 1 (M4)
- [ ] Lock/unlock authority, comment moderation, threat-model deliverable, embed-write escalation (L1–L4)
