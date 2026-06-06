# Test Automation Summary — Story 1.1: Establish the clean-room process gate

**Generated:** 2026-06-06
**Framework:** Python stdlib runner (pytest-compatible, pytest not required) — matches the project's existing gate test pattern.
**Feature under test:** Clean-room provenance merge gate (`docs/clean-room/scripts/check_provenance.py`) + its CI entrypoint (`.github/workflows/clean-room-provenance-gate.yml`).

> Story 1.1 is a process/governance story with **no UI and no HTTP API**. The only
> executable, testable surface is the provenance gate. "E2E" here = invoking the gate
> CLI exactly as CI does (env vars → exit code), which branch protection keys off of.

## Generated Tests

### Unit / decision-logic tests — `docs/clean-room/scripts/test_check_provenance.py`
Extended the existing suite (11 → 23 tests). Added gap coverage:

- [x] `detect_bucket_a`: empty/`None` inputs → not Bucket A; label case + whitespace tolerance.
- [x] `find_provenance_files`: ignores non-`.md` files in the dir; multiple files + whitespace stripping.
- [x] `validate_provenance`: `enterprise/` path excluded (was only `premium/`); excluded path **outside** the Sources block passes (boundary regression guard); missing "Sources Consulted" heading; placeholder-only template row rejected; empty text rejected.
- [x] Real shipped `provenance-record-template.md` read from disk is **rejected** (template-vs-real guard).
- [x] `evaluate`: first-invalid-then-valid → passes; all-invalid → joins each reason.

### E2E tests — `docs/clean-room/scripts/test_gate_e2e.py` (new)
True end-to-end: spawns `check_provenance.py` as a subprocess with CI's env vars
(`PR_LABELS`, `PR_BODY`, `CHANGED_FILES`), asserts process exit code + stdout. Real
on-disk provenance fixtures created/removed under `docs/clean-room/provenance/`.

- [x] Non-Bucket-A PR → exit 0, "PASS", "not Bucket A".
- [x] Bucket-A by label, no provenance → exit 1, "no provenance record".
- [x] Bucket-A by PR-template checkbox, no provenance → exit 1.
- [x] Bucket-A + valid on-disk provenance file → exit 0, names the file.
- [x] Bucket-A + invalid provenance (unchecked attestation) → exit 1, "attestation".
- [x] Labels parsed from mixed comma + newline separation.
- [x] Empty environment → exit 0 (gate not applicable).

## Results

| Suite | File | Tests | Result |
|-------|------|-------|--------|
| Unit  | `test_check_provenance.py` | 23 | ✅ 23/23 |
| E2E   | `test_gate_e2e.py`         | 7  | ✅ 7/7 |
| **Total** | | **30** | ✅ all pass |

Run commands (pytest-free):
```
python3 docs/clean-room/scripts/test_check_provenance.py
python3 docs/clean-room/scripts/test_gate_e2e.py
```

## Coverage

- Gate decision functions (`detect_bucket_a`, `find_provenance_files`, `validate_provenance`, `evaluate`): fully covered including branch/boundary edges.
- CLI entrypoint `main()` (env parsing, disk read, exit codes, stdout): covered end-to-end via subprocess (was 0% before this run).
- Maps to Story 1.1 AC #3 (provenance is a hard merge gate) and Task 6 (validate gate end-to-end).

## Not Covered (out of scope / by design)

- The GitHub Actions YAML runtime itself (requires GitHub runner) — the gate's `Self-test` step in the workflow already runs `test_check_provenance.py`; consider adding `test_gate_e2e.py` to that step.
- Branch-protection "required status check" enforcement — a repo-admin setting outside repo files (documented in `docs/clean-room/merge-gate.md`).

## Next Steps

- Add `python3 docs/clean-room/scripts/test_gate_e2e.py` to the workflow's "Self-test the gate logic" step so the E2E suite also runs in CI.
- Add a provenance fixture per real Bucket A story (1.2–1.7, 1.9) as they land.
