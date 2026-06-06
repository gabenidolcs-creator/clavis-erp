<!--
Behavior-spec template — Bucket A clean-room feature.
Copy this file to docs/clean-room/specs/<feature>.md and fill it in.

RULES (binding):
- Capture BEHAVIOR and UI only — what the feature does, not how the paid product codes it.
- Cite ONLY allowed public sources (see ../allowed-sources.md).
- Do NOT name any premium/enterprise INTERNAL symbol as the thing to replicate.
  Free-core (MIT) symbol names ARE allowed.
- "Influenced by" PE/EE source counts as contamination — see ../implementer-isolation.md.
-->

# Behavior spec — <feature name>

- **Story / epic:** <e.g. 1.3 Kanban view>
- **Bucket:** A (clean-room reimplement)
- **Author:** <name / handle>
- **Date:** <YYYY-MM-DD>

## 1. Allowed sources consulted

List only sources from [allowed-sources.md](../allowed-sources.md). For each, link or
describe how it is publicly accessible.

| # | Source | Type (public docs / public SaaS UI / public issue / MIT free-core) | Link / location |
|---|--------|--------------------------------------------------------------------|-----------------|
| 1 |        |                                                                    |                 |

## 2. Observed behavior (UI / UX)

Describe what the feature does from a user's perspective: screens, controls, states,
inputs, outputs, validation, edge cases. Behavior only — no implementation lifted from
PE/EE source.

## 3. Acceptance behavior

Bullet the externally observable behaviors that the reimplementation must satisfy.

- ...

## 4. Free-core (MIT) symbols to build on

Optional. Free-core MIT base classes / mixins / registries in `backend/src` or
`web-frontend` that the reimplementation will extend (these are ALLOWED).

- ...

## 5. Self-check (must all be true)

- [ ] Every source in §1 is on the allowed-source list (no `premium/`/`enterprise/`,
      no paid-instance internals, no memory of the paid product).
- [ ] No `premium/`/`enterprise/` **internal** symbol is named as the thing to replicate.
- [ ] This spec captures behavior/UI only, not code adapted from PE/EE source.
