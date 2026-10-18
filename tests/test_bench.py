"""Offline ΦRecall evaluation tests. All benchmark inputs are synthetic."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from phicompile.bench import BenchmarkError, benchmark, catalog
from phicompile.core import IntegrityError, ingest, replay, verify

FIXTURES = Path(__file__).resolve().parents[1] / "benchmarks" / "fixtures"
GOLD = FIXTURES / "gold.json"


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.vault = self.root / "vault"
        self.documents = sorted(FIXTURES.glob("*.md"))
        self.assertEqual(len(self.documents), 5)
        for doc in self.documents:
            ingest(self.vault, doc, origin="SIMULATED")

    def replacement_cases(self, transform):
        gold = json.loads(GOLD.read_text(encoding="utf-8"))
        transform(gold)
        file = self.root / "modified.json"
        file.write_text(json.dumps(gold), encoding="utf-8")
        return file

    def test_synthetic_fixture_scores_are_measurable(self):
        result = benchmark(self.vault, GOLD, k=3)
        self.assertEqual(result["case_count"], 10)
        self.assertEqual(result["dataset"], "synthetic_crossrepo_v1")
        self.assertEqual(result["phirecall"]["positive_cases"], 8)
        self.assertEqual(result["phirecall"]["negative_cases"], 2)
        self.assertEqual(result["phirecall"]["no_match_accuracy"], 1.0)
        self.assertGreaterEqual(result["phirecall"]["macro_recall_at_k"], 0.75)
        self.assertGreaterEqual(result["phirecall"]["mean_reciprocal_rank_at_k"], 0.5)
        self.assertIn("baseline", result)
        self.assertTrue(all("query" not in case for case in result["cases"]))
        self.assertTrue(all("source_line_text" not in case for case in result["cases"]))
        self.assertEqual(result["privacy"], "LOCAL_NO_NETWORK_NO_WRITE_NO_SOURCE_EXCERPTS_IN_REPORT")

    def test_deterministic_and_no_write(self):
        before = verify(self.vault)
        source_ledger = (self.vault / "ledger.jsonl").read_bytes()
        fixture_bytes = {doc.name: doc.read_bytes() for doc in self.documents}
        with patch("phicompile.ollama.call_local_ollama",
                   side_effect=AssertionError("benchmark must not invoke a model")):
            first = benchmark(self.vault, GOLD, k=3)
            second = benchmark(self.vault, GOLD, k=3)
        self.assertEqual(first, second)
        self.assertEqual(before, verify(self.vault))
        self.assertEqual(source_ledger, (self.vault / "ledger.jsonl").read_bytes())
        self.assertEqual(fixture_bytes, {doc.name: doc.read_bytes() for doc in self.documents})
        self.assertFalse((self.vault / "output" / "benchmarks").exists())

    def test_catalog_preserves_exact_citation_and_never_promotes(self):
        first = catalog(self.vault, limit=3)
        self.assertEqual(first["returned"], 3)
        self.assertEqual(first["kind"], "PRIVATE_RETRIEVAL_GOLD_CATALOG")
        self.assertIn("PRIVATE EXCERPTS", first["warning"])
        for row in first["entries"]:
            self.assertEqual(row["claim_status"], "INFERRED")
            self.assertFalse(row["claim_verified"])
            self.assertEqual(len(row["source_sha256"]), 64)
            self.assertIn(row["source_line"], (2, 3))
        self.assertEqual({c["status"] for c in replay(self.vault)["claims"].values()}, {"INFERRED"})

    def test_unknown_source_digest_is_not_silently_ignored(self):
        file = self.replacement_cases(lambda gold: gold["cases"][0]["relevant"][0].update(
            source_sha256="0" * 64))
        with self.assertRaises(BenchmarkError):
            benchmark(self.vault, file)

    def test_unknown_line_number_is_not_silently_ignored(self):
        file = self.replacement_cases(lambda gold: gold["cases"][0]["relevant"][0].update(
            source_line=9999))
        with self.assertRaises(BenchmarkError):
            benchmark(self.vault, file)

    def test_duplicate_case_id_rejected(self):
        def modify(gold):
            gold["cases"][1]["id"] = gold["cases"][0]["id"]
        with self.assertRaises(BenchmarkError):
            benchmark(self.vault, self.replacement_cases(modify))

    def test_duplicate_gold_reference_rejected(self):
        def modify(gold):
            gold["cases"][0]["relevant"].append(gold["cases"][0]["relevant"][0])
        with self.assertRaises(BenchmarkError):
            benchmark(self.vault, self.replacement_cases(modify))

    def test_malformed_gold_data_rejected(self):
        def modify(gold):
            gold["cases"][0]["query"] = "the and what"
        with self.assertRaises(BenchmarkError):
            benchmark(self.vault, self.replacement_cases(modify))
        with self.assertRaises(BenchmarkError):
            benchmark(self.vault, GOLD, k=0)
        with self.assertRaises(BenchmarkError):
            benchmark(self.vault, GOLD, k=True)

    def test_bad_case_schema_rejected(self):
        def modify(gold):
            gold["cases"][0]["untrusted"] = "extra field"
        with self.assertRaises(BenchmarkError):
            benchmark(self.vault, self.replacement_cases(modify))

    def test_negative_controls_expose_false_positive_retrieval(self):
        # Deliberately label a query with known positive matches as NO_MATCH.
        # Negative accuracy must fall; the benchmark must not quietly exclude it.
        def modify(gold):
            gold["cases"] = [{"id": "wrong_negative", "query": "source hashes", "relevant": []}]
        result = benchmark(self.vault, self.replacement_cases(modify), k=2)
        self.assertEqual(result["phirecall"]["negative_cases"], 1)
        self.assertEqual(result["phirecall"]["no_match_accuracy"], 0.0)
        self.assertIsNone(result["phirecall"]["macro_recall_at_k"])

    def test_archived_evidence_corruption_prevents_benchmark(self):
        archived = next((self.vault / "sources").glob("*.txt"))
        archived.write_text("altered", encoding="utf-8")
        with self.assertRaises(IntegrityError):
            benchmark(self.vault, GOLD)

    def test_catalog_rejects_bad_limit(self):
        for amount in (0, -1, 201, True):
            with self.subTest(amount=amount), self.assertRaises(BenchmarkError):
                catalog(self.vault, limit=amount)

    def test_report_never_prints_source_excerpts(self):
        result = benchmark(self.vault, GOLD)
        payload = json.dumps(result)
        self.assertNotIn("memory compiler preserves", payload)
        self.assertNotIn("reviewer decisions using hash chaining", payload)
        self.assertNotIn("synthetic source", payload.lower())

    def test_benchmark_provenance_is_source_line_not_filename_only(self):
        case = json.loads(GOLD.read_text(encoding="utf-8"))["cases"][0]
        source_id = case["relevant"][0]["source_sha256"]
        line = case["relevant"][0]["source_line"]
        matching = [c for c in replay(self.vault)["claims"].values()
                    if (c["source_id"], c["line"]) == (source_id, line)]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["status"], "INFERRED")


if __name__ == "__main__":
    unittest.main()
