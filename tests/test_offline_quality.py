"""Offline standard-library tests: no tokens, network, database or model calls."""
import unittest

from scripts.phase3.sanitizer import sanitize
from scripts.phase3.classifier import _layer1
from scripts.phase3.assembler import assemble
from scripts.audit_saved_results import expected_scheme, source_scheme_warning, audit


class InputQualityTests(unittest.TestCase):
    def test_blocks_pan(self):
        self.assertEqual(sanitize("My PAN ABCDE1234F").reason, "pii_pan")

    def test_blocks_aadhaar(self):
        self.assertEqual(sanitize("1234 5678 9012").reason, "pii_aadhaar")

    def test_blocks_email(self):
        self.assertEqual(sanitize("my email is alex@example.com").reason, "pii_email")

    def test_blocks_phone(self):
        self.assertEqual(sanitize("call me at 9876543210").reason, "pii_phone")

    def test_rejects_empty_and_long_queries(self):
        self.assertEqual(sanitize("  ").reason, "empty")
        self.assertEqual(sanitize("x" * 501).reason, "too_long")

    def test_normalizes_markup_and_whitespace(self):
        result = sanitize("  <b>exit</b>    load\n of fund  ")
        self.assertFalse(result.blocked)
        self.assertEqual(result.clean, "exit load of fund")

    def test_rule_based_classifier(self):
        self.assertEqual(_layer1("should i invest in elss"), "ADVISORY")
        self.assertEqual(_layer1("what is the exit load"), "FACTUAL")
        self.assertEqual(_layer1("what is an fd rate"), "OUT_OF_SCOPE")


class DataLineageTests(unittest.TestCase):
    def test_context_carries_primary_source(self):
        chunks = [
            dict(text="Expense ratio value", scheme_name="Scheme A",
                 source_url="https://example.org/a", fetched_at="2026-01-01", similarity=.85),
            dict(text="Other value", scheme_name="Scheme B",
                 source_url="https://example.org/b", fetched_at="2026-01-01", similarity=.75),
        ]
        result = assemble(chunks, top_n=1)
        self.assertEqual(result["chunks_used"], 1)
        self.assertEqual(result["primary_scheme"], "Scheme A")
        self.assertEqual(result["primary_source_url"], "https://example.org/a")
        self.assertNotIn("Other value", result["context"])

    def test_expected_scheme_detection(self):
        self.assertEqual(
            expected_scheme("What is the exit load of Mirae Asset Large Cap Fund?"),
            "Mirae Asset Large Cap Fund",
        )
        self.assertIsNone(expected_scheme("Compare Mirae Asset ELSS Tax Saver Fund and Large Cap Fund"))

    def test_wrong_source_hint_is_flagged(self):
        self.assertTrue(source_scheme_warning(
            "Mirae Asset Large Cap Fund",
            "https://example.org/sid/mirae-asset-elss-tax-saver-fund.pdf",
        ))
        self.assertFalse(source_scheme_warning(
            "Mirae Asset Large Cap Fund",
            "https://example.org/sid/mirae-asset-largecap-fund.pdf",
        ))

    def test_archived_evaluation_issues_detected_not_hidden(self):
        issues = audit()
        self.assertTrue(any("archived FAIL" in s for s in issues))
        self.assertTrue(any("expected Mirae Asset Large Cap Fund" in s for s in issues))
        self.assertTrue(any("possible unrelated source URL" in s for s in issues))


if __name__ == "__main__":
    unittest.main()
