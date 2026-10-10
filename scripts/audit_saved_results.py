"""Audit saved evaluation summaries for provenance and expected-scheme mismatches.

These are archived execution results, not freshly re-run tests. This audit
does not require OpenAI/Supabase credentials or network access.
Use --strict to fail on archived problems; the default prints findings.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def expected_scheme(query: str) -> str | None:
    q = query.lower()
    matches = (
        ("large cap fund", "Mirae Asset Large Cap Fund"),
        ("elss tax saver fund", "Mirae Asset ELSS Tax Saver Fund"),
        ("liquid fund", "Mirae Asset Liquid Fund"),
        ("flexi cap fund", "Mirae Asset Flexi Cap Fund"),
    )
    hits = [name for phrase, name in matches if phrase in q]
    if len(hits) == 1:
        return hits[0]
    # Handle unambiguous abbreviated forms, not general or multi-scheme questions.
    if "mirae asset elss" in q and "large cap" not in q:
        return "Mirae Asset ELSS Tax Saver Fund"
    return None


def source_scheme_warning(expected: str, source_url: str) -> bool:
    """Heuristic only: a clearly different named scheme in a URL is suspicious."""
    s = source_url.lower()
    tokens = {
        "Mirae Asset Large Cap Fund": ("elss", "liquid", "flexi"),
        "Mirae Asset ELSS Tax Saver Fund": ("largecap", "large-cap", "liquid", "flexi"),
        "Mirae Asset Liquid Fund": ("elss", "largecap", "large-cap", "flexi"),
        "Mirae Asset Flexi Cap Fund": ("elss", "largecap", "large-cap", "liquid"),
    }
    return bool(source_url and expected in tokens and any(token in s for token in tokens[expected]))


def audit(saved_root: Path = ROOT) -> list[str]:
    findings: list[str] = []
    reports = {
        "Index": saved_root / "data" / "validation_results.json",
        "Retrieval pipeline": saved_root / "data" / "phase3_test_results.json",
        "Generated answers": saved_root / "data" / "phase4_test_results.json",
    }
    for label, path in reports.items():
        if not path.exists():
            findings.append(f"{label}: archived report missing ({path})")
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        declared = report.get("passed", 0)
        failed = report.get("failed", 0)
        for entry in report.get("tests", []):
            ident = entry.get("test", "(unnamed)")
            if entry.get("status") == "FAIL":
                findings.append(f"{label} / {ident}: archived FAIL")
            if label == "Index" and entry.get("fact_match") is False:
                findings.append(f"{label} / {ident}: expected fact type missing from top hit")
            expected = expected_scheme(entry.get("query", ""))
            if expected and entry.get("type") == "answer":
                retrieved = entry.get("scheme") or entry.get("primary_scheme")
                if retrieved and retrieved != expected:
                    findings.append(f"{label} / {ident}: expected {expected}, got {retrieved}")
                url = entry.get("source_url", "")
                if source_scheme_warning(expected, url):
                    findings.append(f"{label} / {ident}: possible unrelated source URL; verify manually ({url})")
        print(f"{label}: saved report claims {declared} passed, {failed} failed; archive is NOT a fresh run.")
    return findings


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--strict", action="store_true", help="Exit nonzero when archival findings exist")
    args = p.parse_args()
    findings = audit()
    print(f"\nArchived evidence audit: {len(findings)} findings")
    for i, issue in enumerate(findings, 1):
        print(f"  {i}. {issue}")
    print("Live retrieval/generation requires configured API credentials and an independent rerun.")
    return 1 if findings and args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
