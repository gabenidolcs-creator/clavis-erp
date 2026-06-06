#!/usr/bin/env python3
"""Clean-room provenance merge gate (Story 1.1, binding gate (3)).

Blocks merge of any **Bucket A** pull request that lacks a valid provenance record.
Pure decision logic lives in small functions so it is unit-testable without any GitHub
or network access (see test_check_provenance.py). The ``main`` entrypoint wires those
functions to environment variables provided by the CI workflow
``.github/workflows/clean-room-provenance-gate.yml``.

A PR is **Bucket A** when either:
  * it carries the ``bucket-a`` label, or
  * its description checks the "This PR is Bucket A" box in the PR template.

When Bucket A, the PR must add/modify at least one provenance record under
``docs/clean-room/provenance/`` (excluding the template/.gitkeep) that:
  * contains the "## Sources Consulted" heading with at least one listed source,
  * contains the "## Implementer Attestation" heading with the attestation box checked,
  * does not cite an excluded ``premium/`` or ``enterprise/`` path as a source.
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass

PROVENANCE_DIR = "docs/clean-room/provenance/"
BUCKET_A_LABEL = "bucket-a"

# Matches a checked markdown checkbox whose text mentions "Bucket A".
_BUCKET_A_CHECKBOX = re.compile(
    r"^\s*-\s*\[[xX]\].*bucket\s*a", re.MULTILINE | re.IGNORECASE
)
# Matches the checked implementer-attestation checkbox in a provenance record.
_ATTESTATION_CHECKED = re.compile(
    r"-\s*\[[xX]\].*\bclean-room\b", re.IGNORECASE | re.DOTALL
)
# Excluded PE/EE source paths that must never appear as a consulted source.
_EXCLUDED_SOURCE = re.compile(r"(?:^|[\s`/(])(?:premium|enterprise)/", re.IGNORECASE)
# HTML comments hold author guidance (which legitimately mentions premium/enterprise as
# the thing NOT to cite) — strip them before scanning for excluded source paths.
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


@dataclass
class Result:
    passed: bool
    reason: str


def detect_bucket_a(labels: list[str], pr_body: str) -> bool:
    """True if the PR is flagged Bucket A by label or PR-template checkbox."""
    if any(l.strip().lower() == BUCKET_A_LABEL for l in labels):
        return True
    return bool(_BUCKET_A_CHECKBOX.search(pr_body or ""))


def find_provenance_files(changed_files: list[str]) -> list[str]:
    """Provenance records touched by the PR (excludes template and .gitkeep)."""
    out = []
    for path in changed_files:
        p = path.strip()
        if not p.startswith(PROVENANCE_DIR):
            continue
        base = p.rsplit("/", 1)[-1]
        if base in (".gitkeep",) or not base.endswith(".md"):
            continue
        if "template" in base.lower():
            continue
        out.append(p)
    return out


def validate_provenance(text: str) -> Result:
    """Validate a single provenance record's contents."""
    body = text or ""
    sources_match = re.search(r"^##\s+Sources Consulted\s*$", body, re.MULTILINE)
    if not sources_match:
        return Result(False, 'missing "## Sources Consulted" section')
    attest_match = re.search(
        r"^##\s+Implementer Attestation\s*$", body, re.MULTILINE
    )
    if not attest_match:
        return Result(False, 'missing "## Implementer Attestation" section')

    # The Sources Consulted block runs until the next H2 (or EOF).
    sources_block = body[sources_match.end():]
    next_h2 = re.search(r"^##\s+", sources_block, re.MULTILINE)
    if next_h2:
        sources_block = sources_block[: next_h2.start()]
    # Author guidance lives in HTML comments and legitimately mentions premium/enterprise
    # as the thing NOT to cite — strip comments so they don't trip the excluded-path check.
    scan_block = _HTML_COMMENT.sub("", sources_block)
    if _EXCLUDED_SOURCE.search(scan_block):
        return Result(
            False, "cites an excluded premium/ or enterprise/ path as a source"
        )
    # Require at least one real table row (a "| ... |" line with non-placeholder content).
    # Skip the markdown separator and the column-header row ("# | Source | Type | Link").
    def _is_header(line: str) -> bool:
        cells = {c.strip().lower() for c in line.strip().strip("|").split("|")}
        return "source" in cells and "type" in cells

    has_source_row = any(
        line.strip().startswith("|")
        and "---" not in line
        and not _is_header(line)
        and line.strip().strip("|").strip() not in ("", "1")
        and re.sub(r"[|\s\d]", "", line)  # has some actual text beyond | and digits
        for line in scan_block.splitlines()
    )
    if not has_source_row:
        return Result(False, "Sources Consulted lists no actual source")

    if not _ATTESTATION_CHECKED.search(body):
        return Result(False, "implementer attestation checkbox is not checked")
    return Result(True, "valid provenance record")


def evaluate(is_bucket_a: bool, provenance_records: list[tuple[str, str]]) -> Result:
    """Top-level gate decision.

    ``provenance_records`` is a list of ``(path, text)`` for provenance files in the PR.
    """
    if not is_bucket_a:
        return Result(True, "PR is not Bucket A — clean-room gate not applicable")
    if not provenance_records:
        return Result(
            False,
            "Bucket A PR has no provenance record under "
            f"{PROVENANCE_DIR} — merge blocked. Add one from "
            "docs/clean-room/templates/provenance-record-template.md",
        )
    failures = []
    for path, text in provenance_records:
        res = validate_provenance(text)
        if res.passed:
            return Result(True, f"valid provenance record: {path}")
        failures.append(f"{path}: {res.reason}")
    return Result(False, "no valid provenance record — " + "; ".join(failures))


def _read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def main() -> int:
    labels = [
        l for l in re.split(r"[,\n]", os.environ.get("PR_LABELS", "")) if l.strip()
    ]
    pr_body = os.environ.get("PR_BODY", "")
    changed_files = [
        f for f in os.environ.get("CHANGED_FILES", "").splitlines() if f.strip()
    ]

    is_bucket_a = detect_bucket_a(labels, pr_body)
    prov_paths = find_provenance_files(changed_files)
    records = [(p, _read(p)) for p in prov_paths]

    result = evaluate(is_bucket_a, records)
    status = "PASS" if result.passed else "FAIL"
    print(f"clean-room provenance gate: {status} — {result.reason}")
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
