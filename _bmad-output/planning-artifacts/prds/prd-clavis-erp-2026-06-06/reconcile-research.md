# Reconciliation: PRD vs Source Research

**Source research:** `_bmad-output/planning-artifacts/research/technical-airtable-vs-baserow-oss-feature-gap-research-2026-06-05.md`
**Checked against:** `prd.md` + `addendum.md` (prd-clavis-erp-2026-06-06)
**Date:** 2026-06-06
**Method:** Full read of all three docs. Scope filter = the 5 PRD batches (Views, Dashboard charts, Field types, App Builder elements, Collaboration). Deferred items (Button, AI, Run Script, sync connectors, SSO, audit log, mobile, marketplace, Page Designer, Pivot, Org Chart) deliberately NOT re-flagged.

Overall: the PRD is a strong, faithful capture. It actually *adds* rigor beyond the research (security every-surface enforcement, CPM spec, RBAC migration mapping, IDOR/inference-oracle guards) and corrects two research errors (Dashboard module already free; Vue 3 not Vue 2). The gaps below are residual — mostly qualitative content the FR structure dropped, plus a few in-scope behaviors that are referenced but not specified.

---

## GAPS (in-scope, missing or under-specified)

### G1 — Row coloring / decoration is referenced but never scoped (MEDIUM)
- **Research:** lists **row coloring** as a Bucket A *premium* feature (`premium/.../views/decorator_types.py`) — i.e., it does NOT exist in the free tier today. Project memory corroborates.
- **PRD:** FR-3 (Kanban card appearance) says "Card respects row coloring/decoration **if configured**" — it *depends on* row coloring as if it were available, but row coloring has no FR, no Bucket classification, and no clean-room plan.
- **Gap:** A Bucket A dependency is silently assumed. Either (a) add a row-coloring FR/clean-room item, (b) explicitly drop the dependency from FR-3, or (c) state it's out of scope and FR-3 must not assume it. This is already noted in the project's own `review-licensing.md` (item 4) but remains unresolved in `prd.md`/`addendum.md`.

### G2 — Conditional element visibility (App Builder) dropped (LOW–MEDIUM)
- **Research:** §4 App Builder gaps table flags **"Conditional element visibility"** as ⚠️ Partial — "Baserow has basic visibility rules; Airtable more polished." This sits inside Batch 4 (App Builder).
- **PRD:** Batch 4 (§4.8, FR-22–25) covers Chart/Metric/View-embed/Record-review Elements but says nothing about element visibility/conditional rules. Not mentioned anywhere.
- **Gap:** An in-scope App Builder gap from the research has no FR and no explicit non-goal. Decide: in scope (add a consequence/FR) or explicit non-goal.

### G3 — Map provider default was INVERTED vs research's license-clean recommendation (MEDIUM — flag, not omission)
- **Research:** recommends **MapLibre GL JS (BSD) + Nominatim/OSM (ODbL)** as the *default* stack precisely because it is license-clean, key-free, and self-host/cache-friendly. This is stated as the recommendation in two places (§Map View impl, Technology Stack table).
- **PRD/Addendum:** flips this to **Google Maps Platform as the default on cloud**, with OSM/Nominatim only as the self-host fallback. The addendum acknowledges the flip and the Google ToS caching/tiles coupling.
- **Gap:** Not an omission (it's a deliberate, documented decision), but it is a material *divergence* from the source recommendation. The PRD does not state *why* Google-default was chosen over the research's license-clean default (cost? tile quality? geocoding accuracy?). Worth a one-line rationale so the architecture phase doesn't "re-correct" back to MapLibre, and so the added cost/ToS burden on cloud is a conscious tradeoff. Open Q5 partially covers this ("confirm whether forced-Google-everywhere is acceptable") but not the default-choice rationale.

### G4 — Competitive/market framing thinned in the FR body (LOW)
- **Research:** opens with sharp positioning — Airtable $478M ARR / 500k orgs / 80% of Fortune 100; the central "~50–55% free-tier parity vs ~80% full-product" reframe; Kanban called out as "the **biggest single free-tier gap** vs Airtable"; the "almost Airtable but missing X is why teams bounce" thesis.
- **PRD:** §1 Vision captures the parity reframe and the "bounce" thesis well. But the *per-feature* competitive weighting (which gaps are the heaviest free-tier blockers — Kanban #1, comments+personal views next) is flattened: all 5 batches read as equal-priority. The research's relative-impact ranking (High/Medium/Lower-impact tiers) is not reflected in batch ordering or success metrics beyond SM-1's aggregate parity %.
- **Gap:** Minor — sequencing (§13) is dependency-ordered (correct for build), but the *product-value* prioritization from the research (what hurts most in the market) isn't preserved as a tiebreaker if scope must be cut. Consider noting per-batch market weight.

### G5 — Calendar/Timeline behavioral specifics under-specified vs Airtable parity intent (LOW)
- **Research:** Airtable calendar = month + week grids; timeline/Gantt = start+end with day/week/month zoom. PRD FR-4/FR-6 capture month/week and day/week/month zoom — good.
- **Minor under-spec:** Research implies Calendar should handle multi-day/spanning events (date-range, not just single date). PRD FR-4 maps a single "Date Field" only; spanning events (start+end on the calendar, as Airtable supports) aren't addressed. Likely fine for v1 but not stated as a deliberate limit. Consider an `[ASSUMPTION]` like the Kanban single-select one.

### G6 — "Hidden fields per view" (Airtable collab feature) not distinguished from Field Permissions (LOW / likely already-free, verify)
- **Research:** §7 lists Airtable **"Hidden fields per view"** among collaboration features. This is distinct from FR-30 Field *Permissions* (per-role visibility) — it's per-view field visibility, which Baserow free already has.
- **PRD:** FR-1/4/6/12 each say "field visibility applies," implying per-view hiding already works. So this is likely covered by existing core, not a gap — but the PRD never explicitly states per-view field hiding is a preserved baseline, which could cause confusion against the new Field Permissions layer (two different "hide" mechanisms). Worth a one-line glossary/NFR distinction so they aren't conflated during build.

---

## Items deliberately NOT flagged (correctly handled or out of scope)
- Dashboard module + metric Widget already free → PRD corrects the research and scopes only chart Widgets + grouped-aggregate Data Source. Correct.
- Vue 2 → Vue 3 stale note → PRD/addendum correct it. Correct.
- Scatter/line charts (Bucket B), bar/pie (Bucket A) → FR-15 captures all four + bucket tags. Correct.
- Commenter role positioned between Viewer/Editor → FR-29 captures it. Correct.
- Clean-room contamination process, effort estimates, candidate libraries → addendum captures all faithfully (Frappe Gantt MIT, ECharts Apache-2.0, vue-barcode MIT, etc.).
- Autonumber + Running Count (research's "standalone Count" partial gap) → PRD ships BOTH (FR-21/21B), exceeding research. Correct.
- Button, AI, Run Script, sync connectors, SSO, audit log, mobile, marketplace, Page Designer, Pivot, Org Chart → all explicitly deferred per instruction; not flagged.

---

## Severity summary
| ID | Gap | Severity |
|---|---|---|
| G1 | Row coloring referenced (FR-3) but unscoped Bucket A dependency | MEDIUM |
| G3 | Map provider default inverted from research's license-clean rec; no rationale | MEDIUM |
| G2 | Conditional element visibility (App Builder) dropped | LOW–MEDIUM |
| G4 | Per-feature competitive priority weighting flattened | LOW |
| G5 | Calendar multi-day/spanning events not addressed | LOW |
| G6 | Per-view hidden-fields not distinguished from Field Permissions | LOW |
