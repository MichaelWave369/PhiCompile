"""Human review ledger for model-proposed *relationships*, not factual claims.

A human review can accept/reject one suggestion as a useful connection.
It NEVER marks either source claim VERIFIED. Reviewer names are self-asserted
local annotations, not authenticated identities or cryptographic signatures.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import re
from pathlib import Path

from .core import IntegrityError, ZERO_HASH, encode, sha, verify

HEX64 = re.compile(r"[0-9a-f]{64}\Z")
PAIR_ID = re.compile(r"P[0-9]{3}\Z")
VALID_DECISIONS = frozenset(("ACCEPT", "REJECT"))


class ReviewError(ValueError):
    """Invalid review operation, receipt, or review chain."""


def _review_path(vault: Path) -> Path:
    return vault / "reviews" / "decisions.jsonl"


def _validate_reviewer(reviewer: str, note: str) -> None:
    if (not isinstance(reviewer, str) or not 1 <= len(reviewer.strip()) <= 80
            or any(ord(c) < 32 for c in reviewer)):
        raise ReviewError("Reviewer must be a nonempty, single-line local display name (max 80 chars)")
    if (not isinstance(note, str) or not 8 <= len(note.strip()) <= 500
            or any(ord(c) < 32 for c in note)):
        raise ReviewError("A single-line review reason of 8–500 characters is required")


def review_events(vault: Path) -> list[dict]:
    """Validate the local append-only decision ledger against its hash chain."""
    path = _review_path(vault)
    if not path.exists():
        return []
    previous = ZERO_HASH
    result = []
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            item = json.loads(line)
            if not isinstance(item, dict) or item.get("schema_version") != 1:
                raise ReviewError(f"Malformed decision event #{idx}")
            value = item.pop("hash")
            if not isinstance(value, str) or not HEX64.fullmatch(value):
                raise ReviewError(f"Invalid decision hash #{idx}")
            if item.get("prev_hash") != previous or sha(encode(item)) != value:
                raise ReviewError(f"Broken review hash chain at event #{idx}")
            if item.get("sequence") != idx or item.get("decision") not in VALID_DECISIONS:
                raise ReviewError(f"Invalid review event #{idx}")
            if (not isinstance(item.get("receipt_sha256"), str)
                    or not HEX64.fullmatch(item["receipt_sha256"])
                    or not isinstance(item.get("source_ledger_head"), str)
                    or not HEX64.fullmatch(item["source_ledger_head"])
                    or not isinstance(item.get("edge_id"), str)
                    or not item["edge_id"].startswith("proposal:")
                    or item.get("status") != "HUMAN_REVIEWED_CONNECTION"
                    or item.get("truth_status") != "NOT_VERIFIED"):
                raise ReviewError(f"Malformed review identity at #{idx}")
            _validate_reviewer(item.get("reviewer"), item.get("reason"))
            # Important: do not treat this self-reported name as authentication.
            item["hash"] = value
            previous = value
            result.append(item)
        except (ValueError, KeyError, TypeError) as exc:
            raise ReviewError(f"Unreadable review event #{idx}") from exc
    return result


def latest_reviews(vault: Path, ledger_head: str | None = None) -> dict[str, dict]:
    """Most recent decisions per edge; optionally filtered to one source-ledger head."""
    found = {}
    for event in review_events(vault):
        if ledger_head is None or event["source_ledger_head"] == ledger_head:
            found[event["edge_id"]] = event
    return found


def list_reviews(vault: Path) -> dict:
    """Return review state with source ledger integrity checked."""
    current = verify(vault)
    history = review_events(vault)
    latest = latest_reviews(vault, current["ledger_head"])
    return {
        "source_ledger_head": current["ledger_head"],
        "review_events": len(history),
        "review_chain_head": history[-1]["hash"] if history else ZERO_HASH,
        "current_decisions": [
            {
                "edge_id": e["edge_id"], "decision": e["decision"],
                "reviewer": e["reviewer"], "reason": e["reason"],
                "timestamp": e["timestamp"], "sequence": e["sequence"],
                "review_hash": e["hash"], "truth_status": "NOT_VERIFIED",
            }
            for e in sorted(latest.values(), key=lambda value: value["edge_id"])
        ],
        "historical_decisions": len(history) - len([
            event for event in history if event["source_ledger_head"] == current["ledger_head"]
        ]),
    }


def record_review(vault: Path, receipt_sha256: str, pair_id: str, *,
                  decision: str, reviewer: str, reason: str) -> dict:
    """Explicit local review of one current-head Ollama suggestion.

    Requires valid original source evidence, proposal receipt, and existing
    review chain. The source ledger and proposal files are never edited.
    """
    if not isinstance(receipt_sha256, str) or not HEX64.fullmatch(receipt_sha256):
        raise ReviewError("Provide a full 64-character lowercase proposal receipt SHA-256")
    if not isinstance(pair_id, str) or not PAIR_ID.fullmatch(pair_id):
        raise ReviewError("Provide a proposal pair ID such as P001")
    decision = decision.upper() if isinstance(decision, str) else ""
    if decision not in VALID_DECISIONS:
        raise ReviewError("Decision must be ACCEPT or REJECT")
    _validate_reviewer(reviewer, reason)
    before = verify(vault)
    history = review_events(vault)

    # This graph builder validates proposal content hashes, claim IDs, ledger
    # references, provenance line numbers, and current-head compatibility.
    from .graph import build_graph
    graph = build_graph(vault, include_proposals=True)
    receipt_path = vault / "output" / "proposals" / ("proposal-" + receipt_sha256 + ".json")
    if not receipt_path.is_file() or sha(receipt_path.read_bytes()) != receipt_sha256:
        raise ReviewError("Proposal receipt missing or failed SHA-256 integrity")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ReviewError("Proposal receipt is not valid JSON") from exc
    if receipt.get("source_ledger_head") != before["ledger_head"]:
        raise ReviewError("This receipt refers to an older source ledger. Re-run propose first.")
    matches = [
        (i, candidate) for i, candidate in enumerate(receipt["proposals"])
        if isinstance(candidate, dict) and candidate.get("pair_id") == pair_id
    ]
    if len(matches) != 1:
        raise ReviewError("The requested pair ID is not present exactly once in the receipt")
    index, candidate = matches[0]
    edge_id = f"proposal:{receipt_sha256}:{index}"
    edge = next((item for item in graph["links"] if item["id"] == edge_id), None)
    if edge is None or edge.get("kind") != candidate.get("kind"):
        raise ReviewError("Proposal does not match an eligible current-head graph edge")

    # Refuse if another input ingest occurs while review data is prepared.
    if verify(vault)["ledger_head"] != before["ledger_head"]:
        raise ReviewError("Evidence changed during review; no decision recorded")
    history2 = review_events(vault)
    if len(history2) != len(history) or (
        history and history2[-1]["hash"] != history[-1]["hash"]
    ):
        raise ReviewError("Review history changed during operation; retry manually")
    event = {
        "schema_version": 1,
        "sequence": len(history) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "status": "HUMAN_REVIEWED_CONNECTION",
        "truth_status": "NOT_VERIFIED",
        "receipt_sha256": receipt_sha256,
        "pair_id": pair_id,
        "edge_id": edge_id,
        "source_ledger_head": before["ledger_head"],
        "from": edge["from"], "to": edge["to"], "kind": edge["kind"],
        "reviewer": reviewer.strip(), "reason": reason.strip(),
        "prev_hash": history[-1]["hash"] if history else ZERO_HASH,
    }
    event["hash"] = sha(encode(event))
    path = _review_path(vault)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(encode(event).decode("utf-8") + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return {
        "decision": decision,
        "review_hash": event["hash"],
        "sequence": event["sequence"],
        "edge_id": edge_id,
        "source_ledger_head": event["source_ledger_head"],
        "truth_status": "NOT_VERIFIED",
        "note": "Relationship review only: neither original claim is verified or changed.",
    }
