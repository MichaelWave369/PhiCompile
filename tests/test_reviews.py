"""v0.4 human relationship decisions never verify claims or edit originals."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phicompile.core import IntegrityError, ingest, replay, verify
from phicompile.graph import GraphError, build_graph, export_graph
from phicompile.ollama import propose
from phicompile.reviews import (
    ReviewError, latest_reviews, list_reviews, record_review, review_events,
)

MODEL = "granite4.2:8b"


class ReviewGateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.vault = self.root / "vault"
        self.a = self.root / "one.md"
        self.b = self.root / "two.md"
        self.a.write_text("- The synthetic prototype is ready for release.\n", encoding="utf-8")
        self.b.write_text("- The synthetic prototype is not ready for release.\n", encoding="utf-8")
        ingest(self.vault, self.a)
        ingest(self.vault, self.b)

    def receipt(self):
        return propose(self.vault, MODEL, transport=lambda *_: {
            "done": True,
            "model": MODEL,
            "response": json.dumps({"relations": [{
                "pair_id": "P001",
                "kind": "POSSIBLE_CONTRADICTION",
                "rationale": "The two candidate claims disagree on release readiness.",
            }]}),
        })

    def decision(self, receipt, choice="ACCEPT", reason="Related enough for future human review."):
        return record_review(
            self.vault, receipt["proposal_sha256"], "P001",
            decision=choice, reviewer="Local tester", reason=reason,
        )

    def test_accept_marks_connection_not_source_claim(self):
        r = self.receipt()
        before = verify(self.vault)
        original_ledger = (self.vault / "ledger.jsonl").read_bytes()
        original_docs = [self.a.read_bytes(), self.b.read_bytes()]
        decision = self.decision(r)
        self.assertEqual(decision["decision"], "ACCEPT")
        self.assertEqual(decision["truth_status"], "NOT_VERIFIED")
        self.assertEqual(before, verify(self.vault))
        self.assertEqual(original_ledger, (self.vault / "ledger.jsonl").read_bytes())
        self.assertEqual(original_docs, [self.a.read_bytes(), self.b.read_bytes()])
        self.assertEqual({c["status"] for c in replay(self.vault)["claims"].values()}, {"INFERRED"})
        self.assertEqual(build_graph(self.vault)["counts"]["model_proposals"], 0)
        graph = build_graph(self.vault, include_proposals=True)
        edges = [e for e in graph["links"] if e.get("receipt_sha256")]
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["status"], "ACCEPTED_CONNECTION")
        self.assertEqual(edges[0]["review_reason"], "Related enough for future human review.")
        self.assertEqual(graph["counts"]["accepted_connections"], 1)
        self.assertEqual(graph["counts"]["model_proposals"], 1)

    def test_reject_and_latest_review_wins_without_deleting_history(self):
        r = self.receipt()
        first = self.decision(r, choice="ACCEPT")
        second = self.decision(r, choice="REJECT", reason="The scopes are not comparable yet.")
        events = review_events(self.vault)
        self.assertEqual([e["decision"] for e in events], ["ACCEPT", "REJECT"])
        self.assertEqual(events[1]["prev_hash"], first["review_hash"])
        self.assertEqual(events[-1]["hash"], second["review_hash"])
        state = list_reviews(self.vault)
        self.assertEqual(state["review_events"], 2)
        self.assertEqual(len(state["current_decisions"]), 1)
        self.assertEqual(state["current_decisions"][0]["decision"], "REJECT")
        graph = build_graph(self.vault, include_proposals=True)
        edges = [e for e in graph["links"] if e.get("receipt_sha256")]
        self.assertEqual(edges[0]["status"], "REJECTED_CONNECTION")
        self.assertEqual(graph["counts"]["rejected_connections"], 1)

    def test_no_review_without_actual_proposal_receipt(self):
        with self.assertRaises(ReviewError):
            record_review(self.vault, "0"*64, "P001",
                          decision="ACCEPT", reviewer="Mikey",
                          reason="No receipt was generated yet.")
        self.assertEqual(review_events(self.vault), [])

    def test_wrong_pair_id_does_not_record(self):
        r = self.receipt()
        with self.assertRaises(ReviewError):
            record_review(self.vault, r["proposal_sha256"], "P999",
                          decision="ACCEPT", reviewer="Tester",
                          reason="This pair does not exist.")
        self.assertEqual(review_events(self.vault), [])

    def test_receipt_tampering_fails_closed(self):
        r = self.receipt()
        path = Path(r["proposal_file"])
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaises(GraphError):
            self.decision(r)
        self.assertEqual(review_events(self.vault), [])

    def test_stale_evidence_requires_new_proposal(self):
        r = self.receipt()
        self.decision(r)
        third = self.root / "three.md"
        third.write_text("- An unrelated synthetic follow-up statement is recorded.\n", encoding="utf-8")
        ingest(self.vault, third)
        projection = build_graph(self.vault, include_proposals=True)
        self.assertEqual(projection["counts"]["receipts_stale"], 1)
        self.assertEqual(projection["counts"]["model_proposals"], 0)
        self.assertEqual(list_reviews(self.vault)["historical_decisions"], 1)
        with self.assertRaises(ReviewError):
            self.decision(r)
        self.assertEqual(len(review_events(self.vault)), 1)

    def test_tampered_review_chain_fails_graph_and_listing(self):
        r = self.receipt()
        self.decision(r)
        path = self.vault / "reviews" / "decisions.jsonl"
        path.write_text(path.read_text(encoding="utf-8").replace("ACCEPT", "REJECT"),
                        encoding="utf-8")
        with self.assertRaises(ReviewError):
            list_reviews(self.vault)
        with self.assertRaises(ReviewError):
            build_graph(self.vault, include_proposals=True)
        self.assertEqual(verify(self.vault)["sources"], 2)

    def test_control_characters_and_empty_reason_rejected(self):
        r = self.receipt()
        for kwargs in (
            dict(reviewer="Mikey\nRoot", reason="This is explanatory."),
            dict(reviewer="Tester", reason="too short"),
            dict(reviewer="Tester", reason="contains\nnew line"),
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ReviewError):
                    record_review(self.vault, r["proposal_sha256"], "P001",
                                  decision="REJECT", **kwargs)
        self.assertEqual(review_events(self.vault), [])

    def test_invalid_decision_rejected(self):
        r = self.receipt()
        with self.assertRaises(ReviewError):
            self.decision(r, choice="VERIFY")
        self.assertEqual(review_events(self.vault), [])

    def test_review_projection_is_offline_and_html_escapes_notes(self):
        r = self.receipt()
        self.decision(r, reason="Human note: <script>alert(7)</script> is untrusted.")
        result = export_graph(self.vault, include_proposals=True)
        contents = Path(result["viewer"]).read_text(encoding="utf-8")
        self.assertNotIn("<script>alert(7)</script>", contents)
        self.assertIn("ACCEPTED_CONNECTION", contents)
        self.assertIn("HUMAN_REVIEWED_MODEL_SUGGESTION", contents)
        self.assertNotIn("https://", contents)
        self.assertNotIn("fetch(", contents)

    def test_corrupt_original_source_prevents_recording(self):
        r = self.receipt()
        next((self.vault / "sources").glob("*.txt")).write_bytes(b"corrupted")
        with self.assertRaises(IntegrityError):
            self.decision(r)
        self.assertEqual(review_events(self.vault), [])


if __name__ == "__main__":
    unittest.main()
