# Licensing / Clean-Room Review — Clavis ERP Airtable Parity Release PRD

**Scope of this review:** ONLY the licensing/clean-room-reimplementation dimension of `prd.md` + `addendum.md` (Bucket A features derived from Baserow `premium/`+`enterprise/` code under PE/EE licenses). Feature/product soundness, UX, and performance are out of scope here.

**Verdict:** The PRD correctly *names* clean-room as a hard constraint and gets the high-level shape right, but the process is under-specified to be legally defensible, at least one addendum note actively instructs copying the protected pattern, the "study our own product's public UI" path has an unmanaged contamination risk because the engineers already have repo access, and the Bucket A/B classification has two errors. Treat the items below as gates before any Bucket A work starts.

---

## CRITICAL

### [critical] Addendum instructs reuse of the protected source for Field Permissions
- **§ location:** `addendum.md` line 39 — "**Field permissions (A):** Enterprise `field_permissions` pattern; inherits `FieldType.check_can_*`."
- **Problem:** Field Permissions is explicitly classified Bucket A (clean-room required), yet the implementation note tells the engineer to follow the *Enterprise `field_permissions` pattern* and names internal symbols (`field_permissions`, `check_can_*`). This is the single most direct invitation in either document to read and transcribe the protected enterprise source. Naming the protected module/method as the spec is the opposite of clean-room and would taint provenance for FR-30. (Compare line 37 "Row comments (A): reimplement comment model" which is correctly phrased as fresh build, and line 27 "rebuild Vue rendering clean-room" — line 39 breaks that discipline.)
- **Concrete fix:** Rewrite line 39 to describe the *behavior* only, sourced from public docs, with no reference to enterprise symbol names: e.g. "Field Permissions (A): clean-room. Behavior spec = per-field edit/visibility rule enforced server-side via the public `PERMISSION_MANAGERS` extension point. Writer must NOT read `enterprise/.../field_permissions`. Define the `FieldType` permission-check hook fresh." Apply the same scrub to any other note that names a premium/enterprise symbol as the model.

### [critical] No managed barrier against the team's own repo access ("access = taint")
- **§ location:** `prd.md` §3 Glossary def of Clean-room ("engineers who have not read the licensed premium/enterprise source"); §8 Licensing; §11 Risk row 1; `addendum.md` §"Clean-room process".
- **Problem:** Clavis is built *on* Baserow's monorepo, and `premium/` + `enterprise/` ship in that same repo (per project memory). Every engineer with a checkout already has the protected source on disk and very likely has read it. "Built from public docs/UI only, by engineers who have not read the premium source" describes a population that may not exist on this team. The PRD assumes a clean writer pool but specifies no mechanism to (a) identify who is already tainted, (b) physically deny the writer pool access (sparse-checkout / separate repo / access-control on those dirs), or (c) attest non-access. "Studying the public UI/behavior of our OWN premium product" is itself risky: an engineer who has read the source cannot un-know it, and reconstructing from memory is derivative, not clean-room. This is the highest practical risk in the whole strategy and it is currently only named, not controlled.
- **Concrete fix:** Add a concrete barrier mechanism to §8 + addendum: (1) Writer pool must be screened/attested as never having read `premium/`+`enterprise/` (or the specific feature dir); document the attestation. (2) Enforce technically — give writers a sparse checkout / separate clone that excludes `premium/` and `enterprise/`, or revoke their read on those paths during the work. (3) Behavior specs must be authored by the *reader* population (or from genuinely external public sources) and handed to writers; writers may NOT "go look at how our premium Kanban behaves" in the running paid product if they have repo access. (4) If a genuinely clean writer pool is infeasible, escalate to legal for an alternative (e.g., source the behavior spec purely from Airtable public docs + Baserow *public* user-docs, never the product internals).

---

## HIGH

### [high] Clean-room process is deferred/vague — no defined artifacts, owner, or acceptance criteria gate
- **§ location:** `prd.md` §8 ("Process detail belongs in the architecture/eng-process doc; see addendum"); `addendum.md` §"Clean-room process" (4 bullets); §14 Open Q7.
- **Problem:** The actual defensibility of clean-room lives in process specifics, and those are punted to a doc that does not yet exist. The addendum's 4 bullets are the entire process and they are aspirational, not operational: no named owner, no template for the behavior-spec, no defined contents/retention for the provenance log, no definition of what "legal sign-off" must cover or who signs, no per-feature checklist, no go/no-go gate criteria. Open Q7 ("confirm clean-room process owner and legal sign-off path before Bucket A work starts") confirms the owner is still unassigned. A clean-room defense that is "documented somewhere later" is not a defense.
- **Concrete fix:** Before Bucket A starts, produce the eng-process doc with: named **process owner** (DRI) and named **legal approver**; a behavior-spec template (one per Bucket A feature) that records *only* public sources (URLs, screenshots, Airtable/Baserow public docs) with citation; a **provenance log** schema (who wrote, what sources cited, attestation of non-access, reviewer) retained per feature; a reader/writer roster; and an explicit **gate**: no Bucket A code merges until its behavior-spec + provenance log + legal sign-off exist. Reference these artifacts as deliverables, not "belongs downstream."

### [high] Bucket classification errors — two Bucket A features mislabeled as Bucket B
- **§ location:** `prd.md` §4.9 + §6.1 + §8 list vs. project memory.
- **Problem:** The PRD's Bucket A list (§8) is "Kanban, Calendar, Timeline, Dashboard, comments, personal views, Commenter role, field permissions, locked views." But:
  1. **Locked Views** are listed as Bucket A in §8 and §4.9 — correct per Baserow (premium). Good.
  2. **Personal Views** — Bucket A. Correct (premium). Good.
  3. **Interface-only collaborator** and **password-protected share links** are classified **Bucket B / greenfield** (§4.9, §8 "Bucket B features ... interface-only collaborator, password share"). Interface-only collaboration overlaps heavily with Baserow's enterprise/advanced RBAC + application-level permission concepts; calling the *role/permission-manager* purely greenfield is optimistic — the safe-to-copy assumption that flows from a Bucket B label is the danger. Even if the *concept* is new, the implementation rides the same `PERMISSION_MANAGERS` extension and must not be modeled on enterprise RBAC code.
  4. Project memory lists **row coloring** as a Premium (Bucket A) feature. PRD FR-3 says "Card respects row coloring/decoration if configured" — i.e. it *depends on* row coloring — but row coloring is never classified or scoped. If row coloring itself is premium-gated today, FR-3 silently depends on a Bucket A feature that has no FR and no clean-room plan.
- **Concrete fix:** (a) Add an explicit bucket table (feature → A/B → source dir if A → clean-room required Y/N) so classification is auditable and complete for all 5 batches. (b) Re-confirm interface-only collaborator's relationship to enterprise RBAC source; if any enterprise permission code would be the natural reference, treat it as Bucket A regardless of the "new concept" framing. (c) Resolve the row-coloring dependency in FR-3: either scope it as its own Bucket A clean-room item or drop the dependency for v1.

### [high] "Studying public UI/behavior" sourcing is undefined and points at the protected product
- **§ location:** `prd.md` §3 Glossary, §8 ("built from public docs/UI behavior only"); §4.1/§4.2/§4.3 ("Clean-room reimplementation of ... premium Kanban/Calendar/Timeline"); UJ realizations.
- **Problem:** "Public docs/UI behavior" is never pinned to *which* public sources. The features being reimplemented are the team's OWN premium product, so "public UI" most naturally means "open our paid product and watch it" — which, for engineers with repo access, blurs into reading the source and is not a clean external source. A defensible clean-room sources behavior from genuinely independent material (Airtable's public docs, Baserow's public user-docs at a stated URL, public screenshots), not from privileged inspection of the protected implementation.
- **Concrete fix:** Define the *allowed source list* in §8: e.g., Airtable public help center, Baserow public user-docs (cite exact URLs), public marketing/changelogs — and explicitly *disallow* the team's own premium source, premium DB schema, and (for tainted readers) the running premium product as a behavior source. Behavior specs must cite which allowed source each requirement came from (ties into the provenance log).

---

## MEDIUM

### [medium] "Dashboard ... extended with chart types the premium module lacks" reveals knowledge of premium internals
- **§ location:** `prd.md` §4.6 ("extended with chart types the premium module lacks (line, scatter)"); FR-15 ("Line and scatter — absent from the premium module — render correctly"); `addendum.md` line 30 ("extend with line/scatter (absent in premium)").
- **Problem:** Asserting precisely which chart types the premium Dashboards module does/doesn't have is a statement derived from knowing the premium implementation's feature set. That is fine as a *product-scoping* fact (and may be sourceable from public docs), but as written it reads as internal knowledge and, more importantly, it frames the build as "premium module + deltas" rather than a fresh implementation — a framing that invites the writer to start from the premium design. Same risk as the Field Permissions note, lower severity because the rest of §4.6 says "clean-room."
- **Concrete fix:** Reframe to define the target chart set positively from a public source ("Dashboard supports bar/line/pie/doughnut/scatter") and, if the "premium lacks X" claim is retained for product rationale, attribute it to a public source (pricing/docs page) rather than internal knowledge. Drop "premium module + deltas" framing from the build notes.

### [medium] Provenance log named but not required as a merge gate
- **§ location:** `prd.md` §8 ("keep a provenance trail"), §11 ("provenance log"); `addendum.md` line 7 ("keep a provenance log per feature").
- **Problem:** The provenance log is mentioned three times but is never made a *binding* requirement (no FR, no NFR, no acceptance criterion, no CI/merge gate). A provenance artifact that is optional/aspirational provides little legal protection. There is also no statement of what it must contain or how long it is retained.
- **Concrete fix:** Promote the provenance log to a hard gate: add an NFR or release-gate item — "No Bucket A feature merges without a completed provenance log (sources cited, writer attestation of non-access, reviewer sign-off); logs retained for the life of the product." Define the minimum schema (see HIGH process item).

### [medium] No legal sign-off gating wired into the build sequence
- **§ location:** `prd.md` §13 Build Sequencing; §11 Risk row 1 ("Blocks Bucket A work until process is set"); §14 Open Q7.
- **Problem:** §11 says clean-room contamination "Blocks Bucket A work until process is set," which is correct — but §13 Build Sequencing schedules Bucket A work (Kanban/Calendar/Timeline in step 2, Dashboard step 3, Collaboration step 5) without placing the legal-sign-off/process-ready gate as an explicit predecessor in the sequence. The dependency exists in prose (§11, Open Q7) but is not reflected in the ordered plan, so it can be lost in scheduling.
- **Concrete fix:** Add an explicit step 0 to §13: "0. Clean-room process established + legal sign-off obtained (Open Q7). HARD GATE — no Bucket A feature (steps 2 Kanban/Cal/Timeline, 3 Dashboard, 5 Collaboration) may start before this completes." Note that the license-clean Bucket B foundations (step 1) can proceed in parallel without the gate.

### [medium] Glossary clean-room definition is narrower than the real risk (omits "studied/influenced by")
- **§ location:** `prd.md` §3 ("by engineers who have not read the licensed premium/enterprise source").
- **Problem:** The definition gates on "have not *read* the source," but contamination also occurs via being *influenced by* the design (e.g., a tainted engineer pair-programming with, code-reviewing, or verbally guiding the writer; reusing the premium DB schema or API shapes). §11's mitigation does say "reader/writer separation" but the canonical definition is the narrower one and will be the one quoted.
- **Concrete fix:** Broaden the Glossary definition: "...by engineers who have neither read the licensed source nor been materially guided by someone who has; readers must not review, pair on, or direct the free implementation, and must not share the premium schema/API shapes."

---

## LOW

### [low] Trademark / "Airtable parity" branding risk
- **§ location:** Title; §1 Vision ("a free, self-hostable Airtable alternative"); §7 SM-1 "Airtable parity %"; pervasive "Airtable" usage; UJ comparisons.
- **Problem:** "Airtable" is a third-party trademark. Internal planning use is fine, but the framing ("Airtable alternative," "parity %," cloning specific Airtable conventions e.g. FR-19 "follows Airtable's whole-number entry") carries low-level trademark/trade-dress and comparative-advertising risk if it leaks verbatim into product UI, marketing, or public docs. Copying Airtable's *specific UI look* (as opposed to functional behavior) could raise trade-dress concerns separate from the Baserow license issue.
- **Concrete fix:** Add a note in §8 Guardrails: "'Airtable' is used here for internal feature-gap benchmarking only. Public-facing copy must follow trademark guidance (nominative/comparative-use rules); do not adopt Airtable's distinctive visual trade dress. Run marketing/UI copy past legal." Keep parity language out of shipped UI strings (§10 i18n).

### [low] Distinction between functional behavior (copyable) and protected expression not stated
- **§ location:** §8 Licensing, §3 Glossary.
- **Problem:** Clean-room works because *functionality/behavior* is generally not protected by copyright while *the specific source expression* is. The PRD never states this principle, which is the legal basis for why a clean-room reimplementation is permissible at all. Without it, the team may over- or under-constrain (e.g., believing they can't replicate the behavior, or believing paraphrasing the source is enough).
- **Concrete fix:** Add one line to §8: "Clean-room rests on the principle that the licensed *behavior/functionality* may be reimplemented but the licensed *source expression, structure, and naming* may not be copied or paraphrased. Writers reproduce behavior, never code." Confirm exact standard with legal (jurisdiction-dependent).

---

## Summary of required actions before Bucket A starts
1. Scrub `addendum.md` line 39 (and §4.6/line 30) of all premium/enterprise symbol names and "premium + deltas" framing. **[critical]**
2. Define and enforce a clean writer pool with a real access barrier (attestation + sparse/separate checkout); do not rely on inspecting the team's own premium product. **[critical]**
3. Produce the eng-process doc: named owner + legal approver, behavior-spec template, provenance-log schema, reader/writer roster, allowed-source list, and a hard merge gate. **[high]**
4. Add a complete, auditable bucket table for all 5 batches; re-confirm interface-only collaborator and resolve the row-coloring dependency in FR-3. **[high]**
5. Make the provenance log + legal sign-off binding release gates and add them as step 0 of §13 Build Sequencing. **[medium]**
6. Add trademark guidance for "Airtable" usage. **[low]**
