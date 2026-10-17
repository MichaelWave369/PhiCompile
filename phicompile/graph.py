"""ΦGraph v0.4: deterministic read-only projection of governed evidence.

Graph exports are PRIVATE local artifacts. No export changes archived sources,
claims, ledger records, or trust classifications. No network or model call.
"""
from __future__ import annotations

import json
import re
from importlib.resources import files
from pathlib import Path

from .core import IntegrityError, encode, replay, sha, verify

HEX64 = re.compile(r"[0-9a-f]{64}\Z")
MAX_EXPORTED_NODES = 20000
MAX_EXPORTED_EDGES = 120000
RELATION_KINDS = frozenset(("RELATED", "POSSIBLE_CONTRADICTION"))


class GraphError(ValueError):
    """Invalid graph projection input or proposal receipt."""


def _proposal_edges(vault: Path, state: dict, head: str) -> tuple[list[dict], dict]:
    """Include only locally stored, SHA-verified receipts for the current ledger head."""
    directory = vault / "output" / "proposals"
    counts = {"receipts_included": 0, "receipts_stale": 0}
    if not directory.exists():
        return [], counts
    edges = []
    for path in sorted(directory.iterdir(), key=lambda p: p.name):
        if not path.is_file() or not path.name.startswith("proposal-") or not path.name.endswith(".json"):
            continue
        digest = path.name.removeprefix("proposal-").removesuffix(".json")
        if not HEX64.fullmatch(digest):
            raise GraphError("Unexpected proposal filename (expected SHA-256 digest)")
        content = path.read_bytes()
        if sha(content) != digest:
            raise GraphError("Proposal receipt has failed its SHA-256 integrity check")
        try:
            receipt = json.loads(content.decode("utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise GraphError("Proposal receipt contains invalid JSON") from exc
        if (not isinstance(receipt, dict)
                or receipt.get("schema_version") != 1
                or receipt.get("status") != "PROPOSED"
                or receipt.get("trust") != "UNVERIFIED_MODEL_SUGGESTION"
                or not isinstance(receipt.get("proposals"), list)):
            raise GraphError("Proposal receipt does not match supported unverified schema")
        if receipt.get("source_ledger_head") != head:
            counts["receipts_stale"] += 1
            continue
        for index, item in enumerate(receipt["proposals"]):
            if not isinstance(item, dict):
                raise GraphError("Malformed proposal relation")
            a = state["claims"].get(item.get("a"))
            b = state["claims"].get(item.get("b"))
            if (not a or not b or a["id"] == b["id"]
                    or a["source_id"] == b["source_id"]
                    or item.get("kind") not in RELATION_KINDS
                    or item.get("status") != "PROPOSED"
                    or item.get("claim_status") != "INFERRED"
                    or item.get("a_source") != a["source_id"]
                    or item.get("b_source") != b["source_id"]
                    or item.get("a_line") != a["line"]
                    or item.get("b_line") != b["line"]):
                raise GraphError("Proposal contradicts ledger-backed claim provenance")
            rationale = item.get("rationale")
            if not isinstance(rationale, str) or not 8 <= len(rationale) <= 400:
                raise GraphError("Invalid proposal rationale")
            edges.append({
                "id": f"proposal:{digest}:{index}", "from": "claim:" + a["id"],
                "to": "claim:" + b["id"], "kind": item["kind"],
                "status": "PROPOSED", "basis": "LOCAL_MODEL",
                "receipt_sha256": digest, "rationale": rationale,
                "model": str(receipt.get("model_reported", "unknown"))[:120],
            })
        counts["receipts_included"] += 1
    return edges, counts


def build_graph(vault: Path, *, include_proposals: bool = False) -> dict:
    """Project a source/claim/relationship graph from an integrity-verified vault."""
    summary = verify(vault)
    state = replay(vault)
    nodes = []
    links = []
    for source_id, source in sorted(state["sources"].items()):
        if not HEX64.fullmatch(source_id):
            raise IntegrityError("Malformed source digest in ledger")
        nodes.append({
            "id": "source:" + source_id, "kind": "SOURCE",
            "label": source["name"], "origin": source["origin"],
            "sha256": source_id, "event_hash": source["event_hash"],
        })
    for claim_id, claim in sorted(state["claims"].items()):
        if not HEX64.fullmatch(claim_id) or claim["source_id"] not in state["sources"]:
            raise IntegrityError("Invalid claim identifier or source linkage")
        nodes.append({
            "id": "claim:" + claim_id, "kind": "CLAIM",
            "label": claim["text"], "status": claim["status"],
            "source_sha256": claim["source_id"], "source_line": claim["line"],
        })
        links.append({
            "id": "derivation:" + claim_id, "from": "claim:" + claim_id,
            "to": "source:" + claim["source_id"], "kind": "EVIDENCED_BY",
            "status": "TRACEABLE", "basis": "INGEST_LEDGER",
        })
    for edge in sorted(state["edges"].values(), key=lambda e: (e["a"], e["b"], e["kind"])):
        if edge["kind"] not in RELATION_KINDS:
            raise IntegrityError("Unsupported ledger relationship")
        links.append({
            "id": "heuristic:" + sha(encode(edge)),
            "from": "claim:" + edge["a"], "to": "claim:" + edge["b"],
            "kind": edge["kind"], "status": "CANDIDATE", "basis": "DETERMINISTIC_HEURISTIC",
        })
    proposal_counts = {"receipts_included": 0, "receipts_stale": 0}
    if include_proposals:
        proposed, proposal_counts = _proposal_edges(vault, state, summary["ledger_head"])
        from .reviews import latest_reviews
        reviewed = latest_reviews(vault, summary["ledger_head"])
        for edge in proposed:
            review = reviewed.get(edge["id"])
            if review is not None:
                if (review["receipt_sha256"] != edge["receipt_sha256"]
                        or review["from"] != edge["from"]
                        or review["to"] != edge["to"]
                        or review["kind"] != edge["kind"]):
                    raise GraphError("Review receipt disagrees with source-linked proposal")
                edge["status"] = ("ACCEPTED_CONNECTION" if review["decision"] == "ACCEPT"
                                  else "REJECTED_CONNECTION")
                edge["basis"] = "HUMAN_REVIEWED_MODEL_SUGGESTION"
                edge["review_hash"] = review["hash"]
                edge["reviewer"] = review["reviewer"]
                edge["review_reason"] = review["reason"]
                edge["review_timestamp"] = review["timestamp"]
        # A decision refers to one current-head proposal, never an orphan.
        eligible = {edge["id"] for edge in proposed}
        if any(key not in eligible for key in reviewed):
            raise GraphError("A review refers to a missing current-head proposal edge")
        links.extend(proposed)
    if len(nodes) > MAX_EXPORTED_NODES or len(links) > MAX_EXPORTED_EDGES:
        raise GraphError("Graph size exceeds v0.4 export limit; no output written")
    return {
        "schema_version": 1,
        "title": "ΦGraph | Evidence-led knowledge network",
        "trust_notice": "Exploration view only. Claims are unverified candidate extractions; links are evidence pointers or unverified relationship candidates.",
        "ledger_head": summary["ledger_head"],
        "counts": {
            "sources": summary["sources"], "claims": summary["claims"],
            "heuristic_relations": summary["relations"],
            "model_proposals": len([e for e in links if e.get("receipt_sha256")]),
            "accepted_connections": len([e for e in links if e["status"] == "ACCEPTED_CONNECTION"]),
            "rejected_connections": len([e for e in links if e["status"] == "REJECTED_CONNECTION"]),
            **proposal_counts,
        },
        "nodes": nodes,
        "links": sorted(links, key=lambda e: e["id"]),
    }


def export_graph(vault: Path, *, include_proposals: bool = False) -> dict:
    """Generate self-contained offline HTML and JSON inside ignored private vault."""
    graph = build_graph(vault, include_proposals=include_proposals)
    template = files("phicompile").joinpath("assets/graph_viewer.html").read_text(encoding="utf-8")
    if template.count("__PHIGRAPH_JSON__") != 1:
        raise GraphError("Malformed packaged viewer template")
    canonical = encode(graph)
    # Embedded JSON must never be able to terminate a <script type=application/json>
    # block. JS reads data exclusively from textContent and renders with textContent.
    embedded = canonical.decode("utf-8").replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    html = template.replace("__PHIGRAPH_JSON__", embedded)
    target = vault / "output" / "graph"
    target.mkdir(parents=True, exist_ok=True)
    (target / "graph.json").write_bytes(canonical + b"\n")
    (target / "index.html").write_text(html, encoding="utf-8")
    return {
        "status": "LOCAL_EXPORT", "viewer": str(target / "index.html"),
        "graph_json": str(target / "graph.json"),
        "nodes": len(graph["nodes"]), "links": len(graph["links"]),
        "ledger_head": graph["ledger_head"],
        "include_proposals": include_proposals,
        "counts": graph["counts"],
        "note": "Graph files contain source titles and claim text; keep this local private vault off public Pages.",
    }
