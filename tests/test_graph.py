"""PhiGraph acceptance tests, using private temporary vaults only."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phicompile.core import IntegrityError, ingest, replay, verify
from phicompile.graph import GraphError, build_graph, export_graph
from phicompile.ollama import propose

MODEL = "granite4.2:8b"


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.vault = self.root / "private-vault"

    def write(self, filename, content):
        path = self.root / filename
        path.write_text(content, encoding="utf-8")
        return path

    def fixture(self):
        a = self.write("a.md", "- The synthetic prototype is ready for release.\n")
        b = self.write("b.md", "- The synthetic prototype is not ready for release.\n")
        ingest(self.vault, a, origin="OBSERVED")
        ingest(self.vault, b, origin="UNKNOWN")
        return a, b

    def proposal(self):
        return propose(self.vault, MODEL, transport=lambda _payload, _timeout: {
            "done": True, "model": MODEL, "created_at": "2026-10-17T00:00:00Z",
            "response": json.dumps({"relations": [{
                "pair_id": "P001", "kind": "POSSIBLE_CONTRADICTION",
                "rationale": "Release readiness assertions appear logically incompatible.",
            }]}),
        })

    def test_graph_contains_source_claim_evidence_and_conflict(self):
        self.fixture()
        graph = build_graph(self.vault)
        sources = [n for n in graph["nodes"] if n["kind"] == "SOURCE"]
        claims = [n for n in graph["nodes"] if n["kind"] == "CLAIM"]
        derivations = [e for e in graph["links"] if e["kind"] == "EVIDENCED_BY"]
        contradictions = [e for e in graph["links"] if e["kind"] == "POSSIBLE_CONTRADICTION"]
        self.assertEqual((len(sources), len(claims)), (2, 2))
        self.assertEqual(len(derivations), 2)
        self.assertEqual(len(contradictions), 1)
        self.assertEqual(contradictions[0]["status"], "CANDIDATE")
        self.assertIn(sources[0]["origin"], ("OBSERVED", "UNKNOWN"))
        self.assertEqual({n["status"] for n in claims}, {"INFERRED"})
        self.assertTrue(all(n["source_line"] == 1 for n in claims))
        ids = {n["id"] for n in graph["nodes"]}
        self.assertTrue(all(e["from"] in ids and e["to"] in ids for e in graph["links"]))

    def test_empty_graph_is_valid(self):
        graph = build_graph(self.vault)
        self.assertEqual(graph["nodes"], [])
        self.assertEqual(graph["links"], [])
        self.assertEqual(graph["counts"]["sources"], 0)
        exported = export_graph(self.vault)
        self.assertTrue(Path(exported["viewer"]).exists())

    def test_export_is_deterministic_and_does_not_mutate_sources_or_ledger(self):
        original = self.fixture()
        before = verify(self.vault)
        ledger = (self.vault / "ledger.jsonl").read_bytes()
        input_bytes = [p.read_bytes() for p in original]
        output = export_graph(self.vault)
        p = Path(output["graph_json"])
        h = Path(output["viewer"])
        json_one, html_one = p.read_bytes(), h.read_bytes()
        export_graph(self.vault)
        self.assertEqual(p.read_bytes(), json_one)
        self.assertEqual(h.read_bytes(), html_one)
        self.assertEqual(verify(self.vault), before)
        self.assertEqual((self.vault / "ledger.jsonl").read_bytes(), ledger)
        self.assertEqual([p.read_bytes() for p in original], input_bytes)
        graph = json.loads(json_one)
        self.assertEqual(graph["ledger_head"], before["ledger_head"])

    def test_script_termination_in_source_cannot_break_embedded_json(self):
        self.write("evil.md",
                   "- The synthetic note says </script><script>alert('xss')</script> is inert.\n")
        ingest(self.vault, self.root / "evil.md")
        viewer = Path(export_graph(self.vault)["viewer"]).read_text(encoding="utf-8")
        self.assertNotIn("</script><script>alert(", viewer)
        self.assertNotIn("<script>alert(", viewer)
        self.assertIn('script type="application/json"', viewer)
        self.assertIn("textContent", viewer)
        self.assertIn("connect-src 'none'", viewer)
        self.assertIn("</script>", viewer)

    def test_explicit_current_head_proposal_overlay(self):
        self.fixture()
        receipt = self.proposal()
        self.assertEqual(build_graph(self.vault)["counts"]["model_proposals"], 0)
        projected = build_graph(self.vault, include_proposals=True)
        proposed = [e for e in projected["links"] if e["status"] == "PROPOSED"]
        self.assertEqual(len(proposed), 1)
        self.assertEqual(proposed[0]["kind"], "POSSIBLE_CONTRADICTION")
        self.assertEqual(proposed[0]["receipt_sha256"], receipt["proposal_sha256"])
        self.assertEqual(projected["counts"]["receipts_included"], 1)
        self.assertEqual(projected["counts"]["receipts_stale"], 0)
        self.assertTrue(all(c["status"] == "INFERRED" for c in replay(self.vault)["claims"].values()))

    def test_stale_proposal_receipt_is_excluded(self):
        self.fixture()
        self.proposal()
        next_source = self.write("c.md", "- This entirely different statement arrives after proposal time.\n")
        ingest(self.vault, next_source)
        graph = build_graph(self.vault, include_proposals=True)
        self.assertEqual(graph["counts"]["model_proposals"], 0)
        self.assertEqual(graph["counts"]["receipts_stale"], 1)
        self.assertEqual(graph["counts"]["receipts_included"], 0)

    def test_tampered_proposal_receipt_fails_closed(self):
        self.fixture()
        output = self.proposal()
        path = Path(output["proposal_file"])
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaises(GraphError):
            build_graph(self.vault, include_proposals=True)
        self.assertEqual(build_graph(self.vault)["counts"]["model_proposals"], 0)

    def test_corrupt_archived_source_prevents_graph_export(self):
        self.fixture()
        source = next((self.vault / "sources").glob("*.txt"))
        source.write_text("bad data", encoding="utf-8")
        with self.assertRaises(IntegrityError):
            export_graph(self.vault)
        self.assertFalse((self.vault / "output" / "graph").exists())

    def test_corrupt_ledger_prevents_graph_export(self):
        self.fixture()
        ledger = self.vault / "ledger.jsonl"
        ledger.write_text(ledger.read_text() + "{}\n", encoding="utf-8")
        with self.assertRaises(IntegrityError):
            export_graph(self.vault)
        self.assertFalse((self.vault / "output" / "graph").exists())

    def test_no_llm_needed_for_offline_graph(self):
        self.fixture()
        before = verify(self.vault)
        result = export_graph(self.vault)
        self.assertEqual(result["nodes"], 4)
        self.assertEqual(result["include_proposals"], False)
        self.assertEqual(verify(self.vault), before)
        html = Path(result["viewer"]).read_text(encoding="utf-8")
        self.assertNotIn("https://", html)
        self.assertNotIn("fetch(", html)
        self.assertNotIn("XMLHttpRequest", html)


if __name__ == "__main__":
    unittest.main()
