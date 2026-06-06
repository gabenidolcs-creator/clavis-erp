# Story 1.1: Establish the clean-room process gate

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a workspace admin / engineering lead,
I want a legally-signed-off clean-room process in place before any premium feature is reimplemented,
so that Bucket A free-tier work proceeds without contaminating it with protected `premium/`/`enterprise/` source.

## Context & Scope

**This is a process/governance story, not an application-code story.** It produces governance artifacts (an owner assignment, a recorded legal sign-off, an allowed-source list, a behavior-spec template, a provenance-record template) and a **hard merge gate** that blocks any Bucket A pull request lacking a provenance record. No Baserow backend/frontend feature code is written here.

**Why it is first:** Most Epic 1 stories (1.2–1.7, 1.9) and large parts of Epics 2–6 are **Bucket A** — clean-room reimplements of features whose code lives under the PE/EE license in `premium/`/`enterprise/`. The PE/EE license forbids copying, adapting, or being "influenced by" that source. This gate is §13 **step 0** and **blocks ALL Bucket A work until resolved** (Open Q7). [Source: prd.md §13 line 534; architecture.md §line 155, 440]

**The central risk this story exists to neutralize:** the team *already has read access* to `premium/` and `enterprise/` in this repo, so "engineers who have not read premium source" may be a population that does not currently exist. Reconstructing from memory of the paid product is NOT clean-room. The process must structurally resolve this before any Bucket A code is written. [Source: prd.md §8 line 471; §11 line 511]

## Acceptance Criteria

1. **Owner + legal sign-off recorded (Open Q7 resolved).** Given the team has read-access to `premium/` and `enterprise/` dirs, when the clean-room gate is stood up, then a named owner and a recorded legal sign-off exist for the process, **and** an implementer-isolation mechanism exists — either a walled-off group with enforced no-access to `premium/`/`enterprise/`, or external/contracted implementers.

2. **Allowed-source discipline in behavior specs.** Given a behavior spec is authored for a Bucket A feature, when it is reviewed, then it cites only allowed public sources (public Baserow docs, public upstream Baserow SaaS UI, public issues/changelogs), **and** no `premium/`/`enterprise/` internal symbol name appears as the thing to replicate (free-core MIT symbols are allowed).

3. **Provenance record is a hard merge gate.** Given a Bucket A pull request is opened, when it is submitted for merge, then a provenance record (sources consulted + implementer attestation) is required, **and** the merge is blocked without it (provenance log = hard merge gate).

## Tasks / Subtasks

- [ ] **Task 1 — Assign owner & record legal sign-off (AC: #1)** — resolves Open Q7
  - [ ] Assign a named clean-room process owner (engineering lead or delegate) and record it in a tracked governance doc under `docs/`.
  - [ ] Obtain and record legal sign-off on the clean-room process (date, signer, scope). This is the binding prerequisite — Bucket A code cannot start without it.
  - [ ] Decide and document the implementer-isolation model: (a) walled-off internal group with enforced no-access to `premium/`/`enterprise/`, (b) external/contracted implementers, or (c) per-feature legal review of provenance. Record which option(s) apply. [Source: prd.md §8 line 471]
- [ ] **Task 2 — Enforce reader/writer population separation (AC: #1)**
  - [ ] Implement the chosen repo-access barrier for Bucket A implementers (e.g. CODEOWNERS/branch protection, restricted clone of `premium/`+`enterprise/`, or contractor-only implementation). "Influenced by" counts as contamination, not just verbatim copy — document this explicitly. [Source: prd.md §8 line 472 item 4]
  - [ ] Document the separation so reviewers can verify an implementer's eligibility.
- [ ] **Task 3 — Author the allowed-source list & behavior-spec template (AC: #2)**
  - [ ] Create an explicit **allowed-source list**: public Baserow docs, public UI of the *upstream Baserow SaaS*, public issues/changelogs. Explicitly exclude the team's own `premium/`/`enterprise/` source and paid-instance internals. [Source: prd.md §8 line 472 item 2]
  - [ ] Create a behavior-spec template that captures behavior/UI only and forbids naming premium/enterprise internal symbols as the thing to replicate (free-core MIT symbols allowed). [Source: epics.md Story 1.1 AC2]
- [ ] **Task 4 — Create the provenance-record template (AC: #3)**
  - [ ] Define a provenance-record format: sources consulted (from allowed list) + implementer attestation (the implementer affirms no premium/enterprise source was read/used/recalled). [Source: architecture.md lines 239–241]
- [ ] **Task 5 — Wire the provenance gate into the merge process (AC: #3)** — make it structural, not discipline
  - [ ] Add a CI/PR check (or branch-protection required check) that blocks merge of any Bucket A PR lacking a provenance record. No provenance → no merge. [Source: architecture.md line 240, 425]
  - [ ] Define how a PR is flagged Bucket A (label, path heuristic on `core/` Bucket-A dirs, or template checkbox) so the gate knows when to fire.
  - [ ] Document the gate in contributor docs so future agents/contributors follow it.
- [ ] **Task 6 — Validate the gate end-to-end**
  - [ ] Verify a sample Bucket A PR without provenance is blocked, and one with a complete provenance record passes.

## Dev Notes

- **No application feature code in this story.** Deliverables are governance artifacts + a CI/branch-protection merge gate. Do not start any Bucket A feature implementation (Kanban, Calendar, Timeline, RBAC, field permissions, comments, charts, locked/personal views) here — those are blocked until this gate exists and legal sign-off is recorded. [Source: prd.md §13 line 534]
- **Bucket A reimplementations always land in core `backend/src` / `web-frontend`, NEVER in `premium/`/`enterprise/`.** Premium/enterprise may be referenced only for registration *shape* via public MIT symbols, never to copy behavior. This rule is what every downstream Bucket A story relies on this gate to enforce. [Source: architecture.md lines 205, 255]
- **Binding process gates (not advisory)** — all four must be satisfied by this story's artifacts: (1) reader/writer population separation; (2) behavior specs from allowed public sources only; (3) per-feature provenance log as a merge gate; (4) "influenced by" treated as contamination. [Source: prd.md §8 line 472]
- **Downstream consumers:** Stories 1.2–1.7 and 1.9 are `[A]` and each must attach a provenance record per NFR-7 / AR-1 (their AC explicitly requires it). The per-feature test matrix (model → handler → serializer/API → frontend-registry → component) + provenance record is the standard Bucket A definition-of-done. [Source: epics.md Story 1.2 AC3; architecture.md lines 251–253]
- **Anti-patterns (forbidden), carried into the spec/provenance templates:** copying or adapting premium/enterprise source; naming premium/enterprise internal symbols as replication targets; reconstructing from memory of the paid product. [Source: architecture.md line 268; prd.md §8 line 471–472]

### Project Structure Notes

- Governance artifacts belong under `docs/` (project knowledge root per BMM config `project_knowledge: {project-root}/docs`). Suggested home: a `docs/clean-room/` area (owner doc, allowed-source list, behavior-spec template, provenance template, gate docs) — match existing `docs/` conventions for naming/format.
- The merge gate is repo infrastructure (GitHub Actions workflow under `.github/workflows/` and/or branch-protection settings + a PR template checkbox). Follow existing CI workflow conventions in the repo.
- No changes to `backend/src`, `web-frontend/`, `premium/`, or `enterprise/` feature code in this story.

### References

- [Source: epics.md#Epic 1 → Story 1.1: Establish the clean-room process gate] — the three ACs (owner+sign-off+isolation; allowed-source spec; provenance merge gate).
- [Source: prd.md#§8 Licensing (lines 470–472)] — clean-room mandate, repo-access contamination risk, the four binding process gates.
- [Source: prd.md#§11 Risk (line 511)] — clean-room contamination CRITICAL risk; blocks ALL Bucket A; Open Q7 owner unassigned.
- [Source: prd.md#§13 Sequencing (lines 534, 555)] — step 0 process gate; Open Q7 "assign before Bucket A starts".
- [Source: architecture.md (lines 45, 155, 239–241, 425, 437, 440)] — clean-room provenance as merge gate; §13 step 0; provenance MANDATORY for Bucket A.
- [Source: memory baserow-open-core-license-constraint] — paid features need clean-room reimplement; PE/EE license forbids copying.

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.

### File List
