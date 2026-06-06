# Allowed-source list for Bucket A clean-room work

This is binding process gate **(2)**: *behavior specs and implementations for Bucket A
features may draw only from the allowed public sources below.* [Source: prd.md §8 line
472 item 2]

## ✅ Allowed sources

- **Public Baserow documentation** — the published docs at `baserow.io` / the public
  `docs/` of the upstream open-source Baserow repository.
- **Public UI of the upstream Baserow SaaS** — observable behavior and UI of the hosted
  product at `https://baserow.io` (what any user/visitor can see).
- **Public issues, discussions, and changelogs** — upstream public issue tracker,
  discussions, release notes, and changelog entries.
- **Free-core (MIT) source in this repo** — code under `backend/src` and `web-frontend`
  that is MIT-licensed. Free-core **MIT symbol names are allowed** to be referenced and
  reused (registration shape, base classes, mixins, etc.).
- **General public knowledge** — language/framework docs (Django, DRF, Vue, Nuxt),
  public standards, public StackOverflow, etc.

## 🚫 Excluded sources (using these = contamination)

- **`premium/` and `enterprise/` source in this repo** (PE/EE licensed). Do not read,
  copy, adapt, or be *influenced by* it for Bucket A work.
- **Paid-instance internals** — internals of any paid Baserow instance not visible to a
  normal public user.
- **Memory of the paid product** — reconstructing a premium/enterprise feature from
  recollection of having used or read it is NOT clean-room.
- **Premium/enterprise internal symbol names** as *the thing to replicate*. (Referencing
  a free-core MIT symbol is fine; naming a PE/EE-internal class/function as the
  replication target is not.)

## How this is enforced

1. Every Bucket A **behavior spec** must cite only sources from the allowed list — see
   [templates/behavior-spec-template.md](templates/behavior-spec-template.md).
2. Every Bucket A **PR** must attach a **provenance record** listing the sources actually
   consulted (all from the allowed list) plus the implementer attestation — see
   [templates/provenance-record-template.md](templates/provenance-record-template.md).
3. The provenance **merge gate** blocks any Bucket A PR lacking a valid provenance
   record, and the record is rejected if it cites an excluded `premium/`/`enterprise/`
   source — see [merge-gate.md](merge-gate.md).

## References

- [Source: prd.md §8 line 472 item 2]
- [Source: architecture.md lines 205, 255, 268]
