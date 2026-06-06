#!/usr/bin/env python3
"""End-to-end validation of the clean-room provenance merge gate (Story 1.1, Task 6).

Runs with either pytest (``python3 -m pytest``) or plain ``python3 test_check_provenance.py``
so it works in CI and in environments without pytest installed.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from check_provenance import (  # noqa: E402
    detect_bucket_a,
    evaluate,
    find_provenance_files,
    validate_provenance,
)

VALID_PROVENANCE = """# Provenance record — 1.3 Kanban view

- **Implementer:** dev-handle

## Sources Consulted

| # | Source | Type | Link |
|---|--------|------|------|
| 1 | Baserow public docs: views | public docs | https://baserow.io/docs |

## Implementer Attestation

- [x] I affirm this Bucket A reimplementation was produced clean-room; I did not read
      premium/ or enterprise/ source for this feature.
"""

MISSING_ATTESTATION = VALID_PROVENANCE.replace("- [x] I affirm", "- [ ] I affirm")

CITES_EXCLUDED = """# Provenance record

## Sources Consulted

| # | Source | Type | Link |
|---|--------|------|------|
| 1 | premium/baserow_premium/views/kanban.py | internal | n/a |

## Implementer Attestation

- [x] I affirm this Bucket A reimplementation was produced clean-room.
"""

CITES_ENTERPRISE = CITES_EXCLUDED.replace(
    "premium/baserow_premium/views/kanban.py", "enterprise/baserow_enterprise/role.py"
)

# Excluded path appears only in the attestation prose, NOT in Sources Consulted.
# Must still PASS — the gate scopes the exclusion check to the sources block.
EXCLUDED_PATH_OUTSIDE_SOURCES = """# Provenance record

## Sources Consulted

| # | Source | Type | Link |
|---|--------|------|------|
| 1 | Baserow public docs: views | public docs | https://baserow.io/docs |

## Implementer Attestation

- [x] I affirm this was produced clean-room: I did not read premium/ or enterprise/
      source for this feature.
"""

# Sources Consulted contains only the empty template placeholder row.
PLACEHOLDER_SOURCE_ONLY = """# Provenance record

## Sources Consulted

| # | Source | Type | Link |
|---|--------|------|------|
| 1 |        |      |                 |

## Implementer Attestation

- [x] I affirm this was produced clean-room.
"""

MISSING_SOURCES_HEADING = """# Provenance record

## Implementer Attestation

- [x] I affirm this was produced clean-room.
"""


# --- detect_bucket_a -------------------------------------------------------
def test_detect_bucket_a_by_label():
    assert detect_bucket_a(["bucket-a"], "") is True


def test_detect_bucket_a_by_checkbox():
    body = "### Checklist\n- [x] This PR is Bucket A (clean-room reimplement)\n"
    assert detect_bucket_a([], body) is True


def test_detect_not_bucket_a():
    body = "- [ ] This PR is Bucket A (clean-room reimplement)\n"
    assert detect_bucket_a(["database"], body) is False


def test_detect_bucket_a_empty_inputs():
    # No labels and empty/None body must not flag Bucket A.
    assert detect_bucket_a([], "") is False
    assert detect_bucket_a([], None) is False


def test_detect_bucket_a_label_case_and_whitespace():
    # Label match is case-insensitive and whitespace-tolerant.
    assert detect_bucket_a([" Bucket-A "], "") is True


# --- find_provenance_files -------------------------------------------------
def test_find_provenance_files_filters_template_and_gitkeep():
    files = [
        "backend/src/foo.py",
        "docs/clean-room/provenance/.gitkeep",
        "docs/clean-room/templates/provenance-record-template.md",
        "docs/clean-room/provenance/1-3-kanban.md",
    ]
    assert find_provenance_files(files) == ["docs/clean-room/provenance/1-3-kanban.md"]


def test_find_provenance_files_ignores_non_markdown():
    # A non-.md file dropped in the provenance dir is not a provenance record.
    files = ["docs/clean-room/provenance/notes.txt", "docs/clean-room/provenance/x.py"]
    assert find_provenance_files(files) == []


def test_find_provenance_files_multiple_and_whitespace():
    files = [
        "  docs/clean-room/provenance/1-3-kanban.md  ",
        "docs/clean-room/provenance/1-4-calendar.md",
    ]
    assert find_provenance_files(files) == [
        "docs/clean-room/provenance/1-3-kanban.md",
        "docs/clean-room/provenance/1-4-calendar.md",
    ]


# --- validate_provenance ---------------------------------------------------
def test_validate_valid_record():
    assert validate_provenance(VALID_PROVENANCE).passed is True


def test_validate_missing_attestation():
    res = validate_provenance(MISSING_ATTESTATION)
    assert res.passed is False
    assert "attestation" in res.reason


def test_validate_excluded_source():
    res = validate_provenance(CITES_EXCLUDED)
    assert res.passed is False
    assert "excluded" in res.reason


def test_validate_excluded_enterprise_source():
    # enterprise/ paths are excluded just like premium/ paths.
    res = validate_provenance(CITES_ENTERPRISE)
    assert res.passed is False
    assert "excluded" in res.reason


def test_validate_excluded_path_outside_sources_passes():
    # An "premium/"/"enterprise/" mention in the attestation prose is fine —
    # the exclusion is scoped to the Sources Consulted block only.
    assert validate_provenance(EXCLUDED_PATH_OUTSIDE_SOURCES).passed is True


def test_validate_missing_sources_heading():
    res = validate_provenance(MISSING_SOURCES_HEADING)
    assert res.passed is False
    assert "Sources Consulted" in res.reason


def test_validate_placeholder_source_only_is_rejected():
    # The unfilled template row must not count as a real source.
    res = validate_provenance(PLACEHOLDER_SOURCE_ONLY)
    assert res.passed is False
    assert "no actual source" in res.reason


def test_validate_empty_text_is_rejected():
    res = validate_provenance("")
    assert res.passed is False


def test_real_template_file_is_not_a_valid_record():
    # Guards the template-vs-real distinction: the shipped template, read verbatim,
    # must never satisfy the gate (it has only the placeholder row + unchecked box).
    here = os.path.dirname(os.path.abspath(__file__))
    template = os.path.join(
        here, "..", "templates", "provenance-record-template.md"
    )
    with open(template, "r", encoding="utf-8") as fh:
        text = fh.read()
    assert validate_provenance(text).passed is False


def test_validate_template_derived_record_passes():
    # Regression (AC #3): a record authored by copying the shipped template and filling
    # it in (real source row + checked attestation) MUST pass. The template's author
    # guidance legitimately mentions "premium/"/"enterprise/" — kept in an HTML comment so
    # it does not trip the excluded-source check.
    here = os.path.dirname(os.path.abspath(__file__))
    template = os.path.join(
        here, "..", "templates", "provenance-record-template.md"
    )
    with open(template, "r", encoding="utf-8") as fh:
        text = fh.read()
    text = text.replace(
        "| 1 |        |      |                 |",
        "| 1 | Public Baserow docs | docs | https://baserow.io/docs |",
    ).replace("- [ ] I affirm", "- [x] I affirm")
    assert validate_provenance(text).passed is True


def test_validate_guidance_comment_does_not_trip_excluded_source():
    # An HTML comment mentioning premium/ must not be read as a cited source...
    ok = (
        "## Sources Consulted\n"
        "<!-- Do NOT list premium/ or enterprise/ paths. -->\n"
        "| # | Source | Type | Link |\n"
        "|---|--------|------|------|\n"
        "| 1 | Baserow public docs | docs | https://baserow.io/docs |\n"
        "## Implementer Attestation\n"
        "- [x] clean-room affirmed\n"
    )
    assert validate_provenance(ok).passed is True
    # ...but a premium/ path cited in an actual table row still fails.
    bad = (
        "## Sources Consulted\n"
        "| # | Source | Type | Link |\n"
        "|---|--------|------|------|\n"
        "| 1 | premium/fields/handler.py | code | premium/ |\n"
        "## Implementer Attestation\n"
        "- [x] clean-room affirmed\n"
    )
    res = validate_provenance(bad)
    assert res.passed is False
    assert "excluded" in res.reason


# --- evaluate (end-to-end gate decision) -----------------------------------
def test_non_bucket_a_passes():
    assert evaluate(False, []).passed is True


def test_bucket_a_without_provenance_is_blocked():
    res = evaluate(True, [])
    assert res.passed is False
    assert "no provenance record" in res.reason


def test_bucket_a_with_valid_provenance_passes():
    res = evaluate(True, [("docs/clean-room/provenance/1-3-kanban.md", VALID_PROVENANCE)])
    assert res.passed is True


def test_bucket_a_with_invalid_provenance_is_blocked():
    res = evaluate(True, [("p.md", MISSING_ATTESTATION)])
    assert res.passed is False


def test_bucket_a_first_invalid_then_valid_passes():
    # Any one valid record in the PR satisfies the gate.
    res = evaluate(
        True,
        [
            ("bad.md", MISSING_ATTESTATION),
            ("good.md", VALID_PROVENANCE),
        ],
    )
    assert res.passed is True
    assert "good.md" in res.reason


def test_bucket_a_all_invalid_reports_each_reason():
    res = evaluate(
        True,
        [
            ("a.md", MISSING_ATTESTATION),
            ("b.md", CITES_EXCLUDED),
        ],
    )
    assert res.passed is False
    assert "a.md" in res.reason and "b.md" in res.reason


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ok   {t.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"  FAIL {t.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run_all())
