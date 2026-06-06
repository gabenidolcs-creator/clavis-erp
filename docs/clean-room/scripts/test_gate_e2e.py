#!/usr/bin/env python3
"""End-to-end tests for the clean-room provenance merge gate CLI (Story 1.1, Task 6).

Exercises the *actual* entrypoint the CI workflow runs
(``.github/workflows/clean-room-provenance-gate.yml`` invokes
``python3 docs/clean-room/scripts/check_provenance.py``) by spawning the script as a
subprocess with the same environment variables CI provides (``PR_LABELS``, ``PR_BODY``,
``CHANGED_FILES``) and asserting the process exit code and stdout.

This is the integration layer the unit tests in ``test_check_provenance.py`` do not cover:
env-var parsing, on-disk provenance file reading, the PASS/FAIL message, and the exit
code that branch protection keys off of.

Runs with either pytest (``python3 -m pytest``) or plain
``python3 test_gate_e2e.py`` so it works in CI and without pytest installed.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "check_provenance.py")
# Repo root = .../docs/clean-room/scripts -> up three levels.
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PROVENANCE_REL_DIR = "docs/clean-room/provenance"

VALID_PROVENANCE = """# Provenance record — e2e fixture

## Sources Consulted

| # | Source | Type | Link |
|---|--------|------|------|
| 1 | Baserow public docs: views | public docs | https://baserow.io/docs |

## Implementer Attestation

- [x] I affirm this Bucket A reimplementation was produced clean-room; I did not read
      premium/ or enterprise/ source for this feature.
"""

MISSING_ATTESTATION = VALID_PROVENANCE.replace("- [x] I affirm", "- [ ] I affirm")

BUCKET_A_CHECKBOX_BODY = (
    "### Clean-room (Bucket A)\n"
    "- [x] This PR is **Bucket A** (a clean-room reimplementation)\n"
)


def run_gate(*, labels="", body="", changed_files=""):
    """Run the gate CLI as CI does. Returns (returncode, combined_output)."""
    env = dict(os.environ)
    env["PR_LABELS"] = labels
    env["PR_BODY"] = body
    env["CHANGED_FILES"] = changed_files
    proc = subprocess.run(
        [sys.executable, SCRIPT],
        cwd=REPO_ROOT,  # gate reads provenance paths relative to repo root
        env=env,
        capture_output=True,
        text=True,
    )
    return proc.returncode, (proc.stdout + proc.stderr)


class _TempProvenance:
    """Create a real provenance file under the repo provenance dir, then remove it.

    The gate reads files from disk by their repo-relative path, so the fixture must
    live at a real ``docs/clean-room/provenance/<name>.md`` path during the run.
    """

    def __init__(self, name, text):
        self.rel = f"{PROVENANCE_REL_DIR}/{name}"
        self.abs = os.path.join(REPO_ROOT, self.rel)
        self.text = text

    def __enter__(self):
        with open(self.abs, "w", encoding="utf-8") as fh:
            fh.write(self.text)
        return self.rel

    def __exit__(self, *exc):
        try:
            os.remove(self.abs)
        except OSError:
            pass


# --- E2E gate decisions ----------------------------------------------------
def test_e2e_non_bucket_a_passes():
    code, out = run_gate(labels="database", body="just a normal change")
    assert code == 0, out
    assert "PASS" in out
    assert "not Bucket A" in out


def test_e2e_bucket_a_by_label_without_provenance_blocks():
    code, out = run_gate(labels="bucket-a", changed_files="backend/src/foo.py")
    assert code == 1, out
    assert "FAIL" in out
    assert "no provenance record" in out


def test_e2e_bucket_a_by_checkbox_without_provenance_blocks():
    code, out = run_gate(body=BUCKET_A_CHECKBOX_BODY, changed_files="backend/src/foo.py")
    assert code == 1, out
    assert "FAIL" in out


def test_e2e_bucket_a_with_valid_provenance_passes():
    with _TempProvenance("e2e-valid.md", VALID_PROVENANCE) as rel:
        changed = "backend/src/foo.py\n" + rel
        code, out = run_gate(labels="bucket-a", changed_files=changed)
    assert code == 0, out
    assert "PASS" in out
    assert "e2e-valid.md" in out


def test_e2e_bucket_a_with_invalid_provenance_blocks():
    with _TempProvenance("e2e-bad.md", MISSING_ATTESTATION) as rel:
        code, out = run_gate(labels="bucket-a", changed_files=rel)
    assert code == 1, out
    assert "FAIL" in out
    assert "attestation" in out


def test_e2e_labels_parsed_from_comma_and_newline():
    # CI joins labels with commas; be tolerant of newline separation too.
    code, out = run_gate(labels="enhancement,bucket-a\nneeds-review",
                         changed_files="backend/src/foo.py")
    assert code == 1, out
    assert "FAIL" in out


def test_e2e_empty_environment_passes():
    # No labels, no body, no changed files -> not Bucket A -> gate not applicable.
    code, out = run_gate()
    assert code == 0, out
    assert "PASS" in out


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
