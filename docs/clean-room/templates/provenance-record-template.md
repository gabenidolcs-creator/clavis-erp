<!--
Provenance-record template — REQUIRED for every Bucket A PR (binding gate (3)).
Copy this file to docs/clean-room/provenance/<story-or-pr-slug>.md, fill it in, and
include it in the PR. The provenance merge gate (clean-room-provenance-gate) blocks any
Bucket A PR that has no valid provenance record.

The machine gate (docs/clean-room/scripts/check_provenance.py) requires:
  - the heading "## Sources Consulted" with at least one allowed source listed,
  - the heading "## Implementer Attestation" with the attestation checkbox CHECKED,
  - no excluded premium/ or enterprise/ path cited as a source.
Keep those two headings exactly as written.
-->

# Provenance record — <feature / story id>

- **PR / branch:** <link or branch name>
- **Story:** <e.g. 1.3 Kanban view>
- **Bucket:** A (clean-room reimplement)
- **Implementer:** <name / GitHub handle>
- **Date:** <YYYY-MM-DD>

## Sources Consulted

<!--
List every source actually consulted. All must be on the allowed-source list
(see ../allowed-sources.md). Do NOT list premium/ or enterprise/ paths.
-->

| # | Source | Type | Link / location |
|---|--------|------|-----------------|
| 1 |        |      |                 |

## Implementer Attestation

- [ ] I affirm that this Bucket A reimplementation was produced **clean-room**: I did
      **not** read, copy, adapt, or rely on memory of any `premium/` or `enterprise/`
      (PE/EE) source for this feature, and I was not *influenced by* it. Every source I
      used is listed above and is on the allowed-source list.

**Implementer signature / handle:** _____________________   **Date:** ____________

## Reviewer confirmation (filled at review)

- [ ] Reviewer verified implementer eligibility per implementer-isolation.md.
- [ ] Reviewer verified all sources above are on the allowed-source list.
