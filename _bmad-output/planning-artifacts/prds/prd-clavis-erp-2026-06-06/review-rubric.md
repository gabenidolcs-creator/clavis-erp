# PRD Quality Review — Clavis ERP Airtable Parity Release

## Overall verdict

This is a strong, build-ready PRD with a genuine thesis (close the Airtable free-tier gap by clean-room reimplementing paywalled features and building the truly missing ones) that propagates coherently from Vision through FRs, sequencing, and metrics. Its standout qualities are the load-bearing Bucket A/B licensing distinction that drives scope, risk, and build order; testable consequences on nearly every FR; and honest counter-metrics that protect the differentiators. The main risks are localized: SM-1 (the headline parity metric) rests on an unconfirmed 80% threshold and an externally-defined feature matrix, and a handful of NFR/metric budgets remain "agreed threshold" placeholders that downstream story creation will trip on.

## Decision-readiness — strong

Decisions are stated as decisions, not buried. FR-10's "prompt-first reschedule" is chosen explicitly and the rejected alternative (silent cascade) is implied by the "not silently broken" language in the decline branch. The Map provider decision (§4.5, §8) is the model case: it names the choice (Google default on cloud, configurable OSM/Nominatim for self-host), the reason (Google ToS forbids long-term caching and non-Google tiles), and what that costs self-hosters. The Autonumber-vs-Running-Count tension is resolved by shipping both *with* a rationale ("they serve different jobs"), not by dodging.

Trade-offs are named with what's given up: the Button field is deferred *because* automations are out of scope (§5), barcode is display-only *because* camera scanning needs a native app that doesn't exist, and the "feature-complete, not phased-ship" release gate (§11 Scope risk) is an explicit posture rather than a hedge.

Open Questions (§14) are genuinely open where they remain — Q1 (parity target + matrix), Q6 (embed interactivity), Q7 (clean-room legal owner), Q8 (percent convention) — and the resolved ones are struck through with their resolution recorded, which is honest bookkeeping rather than rhetorical Q&A.

### Findings
- **medium** Headline metric depends on an unowned external artifact (§7 SM-1, §14 Q1) — "move free-tier parity ... to ≥80% on the same tracked feature set ... re-score the research feature matrix" with `[ASSUMPTION: 80% target — confirm exact threshold]`. The single primary success metric is gated on both an unconfirmed number and a matrix whose scoring method/owner isn't specified. A decision-maker can't yet tell whether the release "succeeded." *Fix:* before build, freeze the feature matrix version and scoring rubric, and convert the 80% from assumption to committed target (or state the band, e.g. 78–82%).

## Substance over theater — strong

Little furniture here. The Vision (§1) is product-specific — it names the actual gap (~50–55% parity), the actual paywalled features, the actual differentiators (WebSocket sync, unlimited records, two-way Postgres sync), and the actual bounce reason ("almost Airtable, but missing X"); it would not swap into a generic PRD. The JTBD list (§2.1) is concrete and maps to features. Non-Users (§2.2) earn their place by gating scope decisions (mobile gates camera scanning; automation depth gates the Button field).

NFRs (§10) avoid boilerplate by citing project-specific mechanics: `get_order_by_field_string` for field ordering, `PERMISSION_MANAGERS` hookpoints, existing virtual-scroll patterns, the model→handler→serializer→registry→component test matrix. That's earned, not copied. The differentiator claims are not innovation theater — they're framed as things to *preserve/not regress*, with counter-metrics (SM-C1/C2/C3) enforcing them.

One soft spot: there are no named personas as standalone artifacts; personas live inside the UJs. That is the right call for this shape (see Shape fit) and is not theater — but it means "persona" scrutiny is N/A rather than passed.

## Strategic coherence — strong

The thesis is explicit and the document bets on it: clean-room reimplement Bucket A, greenfield Bucket B, keep it all in the free tier, don't regress the differentiators. Prioritization follows the thesis rather than ease — §13 sequences license-clean foundations first *to de-risk*, which serves the legal thesis, not a "what's easy" ordering (though it happens to also be low-risk, the stated reason is dependency + license-clean unblocking).

Success metrics validate the thesis rather than measuring raw activity: SM-1 measures parity (the whole point), and the secondary metrics are scoped to feature clusters (SM-2→views, SM-3→collaboration, SM-4→data viz). Counter-metrics are present and pointed — SM-C2 ("free-tier record limits stay unlimited ... don't reach parity by Airtable-style gating") is a real guardrail against winning the metric the wrong way. MVP scope is a coherent "problem-solving + parity" kind, and the scope logic (close the largest gaps, defer the automation-dependent and AI items) matches.

### Findings
- **low** Secondary metrics measure adoption breadth but not the thesis's quality claim (§7 SM-2/SM-4) — the Vision argues teams can "actually run their business on" Clavis, but SM-2 counts bases that "create at least one new View type" and SM-4 counts dashboards/pages created. Creation is not sustained use. *Fix:* consider a retention/repeat-use cut (e.g. views still active at 60 days) on at least one secondary metric to validate the "run their business on it" claim, not just trial.

## Done-ness clarity — strong

This is the document's strongest dimension and the one downstream leans on hardest. Nearly every FR carries explicit "Consequences (testable)" with verifiable conditions: FR-2 specifies the null-on-Uncategorized behavior, real-time broadcast, and rollback-on-failure; FR-9 requires cycle rejection "with a clear error"; FR-10 enumerates confirm/decline branches and single-step undo; FR-30 demands server-enforced 403 *and* API-level field omission "not UI-only." Permission FRs consistently specify server-side enforcement and 403s, which is exactly the bounded language story creation needs.

The adjective-policing bar is mostly met — the PRD even pre-empts itself by pushing soft budgets into §10 rather than leaving them vague inline.

### Findings
- **medium** Performance bounds are deferred to placeholders that don't yet exist (§4.6 NFR, §7 SM-C3, §10) — "renders initial paint within an acceptable budget (defined in §10)" but §10 says only "do not regress beyond an agreed threshold"; SM-C3 likewise says "agreed threshold." The budget is promised in two places and delivered in neither, and the widget/row figure is `[ASSUMPTION: 12]`/100k. An engineer cannot test "done" for dashboard perf. *Fix:* set concrete numbers (e.g. p75 initial paint ≤ X ms at 12 widgets / 100k rows; bundle delta ≤ Y kB gz) or explicitly mark them as architecture-phase deliverables with an owner.
- **low** A few residual soft phrases (§13, §10 a11y) — §13 leans on "confirm/refine in architecture"; §10 accessibility is "where feasible" with `[ASSUMPTION: WCAG 2.1 AA]`. Acceptable as scoped deferrals, but "where feasible" on keyboard nav is a future story-scoping argument. *Fix:* name which interactions are in-bound for v1 a11y vs. explicitly deferred.

## Scope honesty — strong

Omissions are explicit and do real work. §5 Non-Goals is substantive and each entry carries its *reason* (no automations → Button deferred; barcode display-only → no native app). §6.2 restates out-of-scope at the MVP level with a `[NOTE FOR PM]` on the Button deferral. De-scoping is done out loud: FR-25 carries `[NON-GOAL for MVP]` AI review layouts; FR-20 carries an inline "Out of Scope: camera scanning."

Assumptions are tagged inline and the §9 index is real (12 entries). Open-items density is appropriate for a green-light-to-build PRD: most high-stakes questions are RESOLVED (Q2/Q3/Q4/Q5 struck through), and the remaining open items (Q1, Q6, Q7, Q8) are correctly flagged rather than papered over. The count is not alarming for a release of this size.

### Findings
- **medium** Two open items are build-blocking but not labeled as gates (§14 Q7, §6.2) — Q7 ("clean-room process owner and legal sign-off path before Bucket A work starts") and the Q6 embed-interactivity question both block real work (§11 states clean-room contamination "Blocks Bucket A work until process is set"). They sit in a flat Open Questions list alongside the cosmetic Q8. *Fix:* mark Q7 as a hard gate on Bucket A start and Q6 as a gate on FR-24 story creation, so sequencing doesn't proceed past them silently.
- **low** A possible scope-honesty drift between §6.2 and Q4 (§6.2, §14 Q4, FR-30) — §6.2 lists "Field *hiding* by permission (vs. edit-restriction) — confirm whether v1 or follow-on" as still-open, but Q4 is struck through as RESOLVED (v1 includes hide-by-permission) and FR-30 fully specifies hidden-field behavior. The Out-of-Scope list contradicts the resolved decision. *Fix:* remove the field-hiding line from §6.2 to match the resolved FR-30 / Q4.

## Downstream usability — strong

This PRD is chain-top (it explicitly feeds architecture/epics/UX per §0) so traceability matters, and it largely delivers. The Glossary (§3) is thorough and domain nouns are used consistently (View Type, Field Type, Bucket A/B, Data Source, Element all reused verbatim across FRs and §12). FR IDs are unique and the "Realizes UJ-N" and "Realizes FR-N" back-references mostly resolve. Each batch section reads coherently when pulled out alone; §12 Integration and §13 Build Sequencing give architecture clean extraction points, and the addendum cleanly quarantines tech choices so the FRs stay implementation-neutral.

### Findings
- **medium** FR ID sequence has a non-contiguous insert that breaks naive range references (§4.7 FR-21B, §7) — Autonumber is FR-21 and Running Count is FR-21B (inserted to avoid renumbering). SM-1 then says "FR-1 through FR-33" and §7/§13 reference ranges like "FR-18–21B"; a tool or reader iterating FR-1..FR-33 will miss FR-21B. *Fix:* either renumber to make IDs contiguous (FR-21 Autonumber, FR-22 Running Count, shift the rest) or add a note that FR-21B exists outside the numeric range wherever ranges are cited.
- **low** "Realizes UJ-1" is overloaded across unrelated FRs (§4, multiple) — UJ-1 (Maya: board + dashboard) is cited by FR-1, FR-22, FR-26, FR-15(implied via §4.6), etc. Some are legitimate (dashboard), but FR-26 row comments citing UJ-1 is a stretch (UJ-1 has no comment beat). *Fix:* tighten Realizes tags to UJs whose path actually exercises the FR, so UJ→FR traceability stays trustworthy.

## Shape fit — strong

The shape matches the product. This is a multi-stakeholder, UX-heavy consumer/B2B product, so the five UJs with named protagonists (Maya, Diego, Priya, Sam, Rosa) are load-bearing and correctly used — each has persona+context, entry state, path, climax, resolution, and a Realizes-FR mapping. None float. It is not over-formalized: there's no separate persona section padding the doc, and operational NFRs sit alongside user-facing UJs appropriately.

The brownfield reality is handled well — existing-code references (`PERMISSION_MANAGERS`, `get_order_by_field_string`, the registries, "Grid/Gallery/Form exist today") are concrete and the new-vs-existing line is clear (Bucket A reimplements existing-but-paywalled; Bucket B is greenfield). The §8 note correcting the research doc's stale "Vue 2" against the authoritative repo (Vue 3) is exactly the brownfield accuracy the rubric asks for. No shape mismatch found.

## Mechanical notes

- **Glossary drift:** minimal. "App Builder"/"Application Builder" are reconciled in §3 ("Application Builder (App Builder)"). "Running Count" vs the existing relational "Count" is explicitly disambiguated in both Glossary and FR-21B. No case/plural drift of note.
- **ID continuity:** FR IDs run FR-1..FR-33 with FR-21B inserted (see Downstream finding) — unique but not strictly contiguous. UJ-1..UJ-5 and SM-1..SM-4 / SM-C1..SM-C3 are contiguous and unique. Cross-references ("see §11", "§4.6", "FR-9–FR-11") resolve.
- **Assumptions Index roundtrip:** §9 has 12 entries. Spot-check: inline assumptions at §4.1, §4.4, §4.5, §4.6 FR-15, §4.6 NFR, §4.7 FR-19, §4.7 FR-21B, §4.8 FR-24, §4.9 FR-27, §7 SM-1, §7 SM-2 all appear in the index. The §10 a11y `[ASSUMPTION: WCAG 2.1 AA]` and the FR-21B "condition scope" assumption are present inline but the a11y one is **not** listed in §9 — minor roundtrip gap. Resolved assumptions (FR-10, FR-21/21B) are marked RESOLVED in the index, which is good practice.
- **UJ protagonist naming:** all five UJs carry a named protagonist with inline context. UJ-5 (Rosa) omits an explicit "Entry state" line that the other four have — cosmetic inconsistency.
- **Required sections:** all expected sections for a chain-top, build-ready PRD are present (Vision, Target User/JTBD/UJs, Glossary, Features/FRs, Non-Goals, MVP Scope, Success Metrics + counter-metrics, Constraints, Assumptions Index, NFRs, Risk, Integration, Build Sequencing, Open Questions) plus a well-scoped addendum for tech choices.
