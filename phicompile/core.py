"""Deterministic v0.1 compiler. Inputs are evidence, never instructions."""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
from pathlib import Path

MAX_SOURCE_BYTES = 1_048_576
MAX_CLAIMS = 500
ORIGINS = ("OBSERVED", "VERIFIED", "INFERRED", "DREAMED", "SIMULATED", "UNKNOWN")
ZERO_HASH = "0" * 64


class IntegrityError(RuntimeError):
    """Ledger or archived evidence does not match its recorded digest."""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode(obj: dict) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def init(vault: Path) -> None:
    for folder in ("sources", "wiki", "output"):
        (vault / folder).mkdir(parents=True, exist_ok=True)


def events(vault: Path) -> list[dict]:
    log = vault / "ledger.jsonl"
    if not log.exists():
        return []
    result = []
    previous = ZERO_HASH
    for number, line in enumerate(log.read_text(encoding="utf-8").splitlines(), 1):
        try:
            event = json.loads(line)
            recorded_hash = event.pop("hash")
            if event.get("prev_hash") != previous or sha(encode(event)) != recorded_hash:
                raise IntegrityError(f"Broken ledger chain at event {number}")
            if event.get("kind") != "INGEST":
                raise IntegrityError(f"Unsupported event type at {number}")
        except (ValueError, KeyError, TypeError) as exc:
            raise IntegrityError(f"Unreadable event {number}") from exc
        event["hash"] = recorded_hash
        previous = recorded_hash
        result.append(event)
    return result


def replay(vault: Path) -> dict:
    state = {"sources": {}, "claims": {}, "edges": {}}
    for event in events(vault):
        source_id = event["source_id"]
        if source_id in state["sources"]:
            raise IntegrityError(f"Duplicate source in ledger: {source_id}")
        state["sources"][source_id] = {
            "id": source_id,
            "name": event["source_name"],
            "origin": event["origin"],
            "event_hash": event["hash"],
        }
        for claim in event["claims"]:
            cid = claim["id"]
            if cid in state["claims"]:
                raise IntegrityError(f"Duplicate claim: {cid}")
            state["claims"][cid] = claim
        for edge in event["edges"]:
            key = (edge["a"], edge["b"], edge["kind"])
            state["edges"][key] = edge
    for edge in state["edges"].values():
        if edge["a"] not in state["claims"] or edge["b"] not in state["claims"]:
            raise IntegrityError("Relation points to an unknown claim")
    return state


def verify(vault: Path) -> dict:
    state = replay(vault)
    for source_id in state["sources"]:
        archived = vault / "sources" / (source_id + ".txt")
        if not archived.is_file() or sha(archived.read_bytes()) != source_id:
            raise IntegrityError(f"Source snapshot missing or altered: {source_id}")
    return {
        "sources": len(state["sources"]),
        "claims": len(state["claims"]),
        "relations": len(state["edges"]),
        "ledger_head": events(vault)[-1]["hash"] if events(vault) else ZERO_HASH,
    }


def extract(source_id: str, content: str) -> list[dict]:
    """Conservative line-level candidates, not fact verification or NLP."""
    claims = []
    for line_no, line in enumerate(content.splitlines(), 1):
        statement = line.strip()
        if statement.startswith(("- ", "* ")):
            statement = statement[2:].strip()
        if (not statement or statement.startswith(("#", "```"))
                or len(statement) < 12 or len(statement) > 480):
            continue
        cid = sha(f"{source_id}:{line_no}:{statement}".encode("utf-8"))
        claims.append({
            "id": cid, "source_id": source_id, "line": line_no,
            "text": statement, "status": "INFERRED",
        })
        if len(claims) >= MAX_CLAIMS:
            break
    return claims


def normalized_statement(text: str) -> tuple[str, bool]:
    clean = re.sub(r"[.!?]+$", "", text.lower().strip())
    negative = bool(re.search(r"\b(is|are|was|were|can|will|has|have)\s+not\b", clean))
    canonical = re.sub(r"\b(is|are|was|were|can|will|has|have)\s+not\b", r"\1", clean)
    return " ".join(canonical.split()), negative


def keywords(text: str) -> set[str]:
    stop = {"the", "and", "for", "with", "from", "that", "this", "have", "has",
            "are", "was", "were", "not", "into", "about", "will", "can", "its"}
    return {word for word in re.findall(r"[a-z0-9]+", text.lower())
            if len(word) > 2 and word not in stop}


def relation(a: dict, b: dict) -> str | None:
    if a["source_id"] == b["source_id"]:
        return None
    norm_a, neg_a = normalized_statement(a["text"])
    norm_b, neg_b = normalized_statement(b["text"])
    if norm_a == norm_b and neg_a != neg_b:
        return "POSSIBLE_CONTRADICTION"
    terms_a, terms_b = keywords(a["text"]), keywords(b["text"])
    common = terms_a & terms_b
    if len(common) >= 3 and len(common) / max(1, len(terms_a | terms_b)) >= 0.35:
        return "RELATED"
    return None


def ingest(vault: Path, input_path: Path, origin: str = "UNKNOWN") -> dict:
    if origin not in ORIGINS:
        raise ValueError("Invalid provenance origin")
    if not input_path.is_file() or input_path.suffix.lower() not in (".txt", ".md"):
        raise ValueError("Only existing UTF-8 .txt and .md files are supported")
    data = input_path.read_bytes()
    if len(data) > MAX_SOURCE_BYTES:
        raise ValueError("Input exceeds 1 MiB limit")
    content = data.decode("utf-8")
    init(vault)
    current = verify(vault)
    state = replay(vault)
    source_id = sha(data)
    if source_id in state["sources"]:
        return {"added": False, "source_id": source_id, "claims": 0, "relations": 0}
    claims = extract(source_id, content)
    edges = []
    old_claims = list(state["claims"].values())
    for incoming in claims:
        for previous in old_claims:
            kind = relation(incoming, previous)
            if kind:
                edges.append({"a": min(incoming["id"], previous["id"]),
                              "b": max(incoming["id"], previous["id"]), "kind": kind})
    archived = vault / "sources" / (source_id + ".txt")
    # Immutable content-addressed snapshots. Original file is never changed.
    try:
        fd = os.open(archived, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if sha(archived.read_bytes()) != source_id:
            raise IntegrityError("Existing snapshot failed checksum")
    else:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    event = {
        "kind": "INGEST", "source_id": source_id, "source_name": input_path.name,
        "origin": origin, "claims": claims, "edges": edges,
        "prev_hash": current["ledger_head"],
    }
    event["hash"] = sha(encode(event))
    with (vault / "ledger.jsonl").open("a", encoding="utf-8") as log:
        log.write(encode(event).decode("utf-8") + "\n")
        log.flush()
        os.fsync(log.fileno())
    return {"added": True, "source_id": source_id, "claims": len(claims), "relations": len(edges)}


def compile_wiki(vault: Path) -> dict:
    """Rebuild generated outputs only; original inputs and ledger remain untouched."""
    summary = verify(vault)
    state = replay(vault)
    init(vault)
    wiki = vault / "wiki"
    # All output page names derive from digests, never from untrusted filenames.
    for cid, claim in sorted(state["claims"].items()):
        related = [edge for edge in state["edges"].values()
                   if cid in (edge["a"], edge["b"])]
        source = state["sources"][claim["source_id"]]
        lines = [
            "# Claim " + cid[:12], "",
            "**Status:** INFERRED (candidate extraction, not verified truth)",
            "**Source:** " + html.escape(source["name"]) + " (line " + str(claim["line"]) + ")",
            "**Source origin:** " + source["origin"],
            "**SHA-256:** " + claim["source_id"], "",
            "> " + html.escape(claim["text"]), "", "## Connections", "",
        ]
        for edge in sorted(related, key=lambda e: (e["kind"], e["a"], e["b"])):
            other = edge["b"] if edge["a"] == cid else edge["a"]
            lines.append("- **" + edge["kind"] + "**: [Claim " + other[:12] +
                         "](claim-" + other + ".md)")
        if not related:
            lines.append("- No cross-source candidates yet.")
        (wiki / ("claim-" + cid + ".md")).write_text("\n".join(lines) + "\n", encoding="utf-8")
    index = ["# ΦCompile generated knowledge index", "",
             "All claims are candidate extractions. None are automatically verified.", ""]
    for cid, claim in sorted(state["claims"].items()):
        index.append("- [Claim " + cid[:12] + "](claim-" + cid + ".md): " +
                     html.escape(claim["text"][:120]))
    (wiki / "INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    contradictions = [e for e in state["edges"].values()
                      if e["kind"] == "POSSIBLE_CONTRADICTION"]
    report = [
        "# ΦCompile compilation receipt", "",
        "This report is generated from a tamper-evident SHA-256 hash chain.",
        "It is not proof that claims are true or that authors are authenticated.", "",
        "- Sources: " + str(summary["sources"]),
        "- Candidate claims: " + str(summary["claims"]),
        "- Cross-source relations: " + str(summary["relations"]),
        "- Possible contradictions: " + str(len(contradictions)),
        "- Ledger head: " + summary["ledger_head"], "",
        "## Contradictions requiring human review", "",
    ]
    for edge in sorted(contradictions, key=lambda e: (e["a"], e["b"])):
        report.append("- " + edge["a"][:12] + " ↔ " + edge["b"][:12])
    if not contradictions:
        report.append("- None detected by the limited v0.1 heuristic.")
    (vault / "output" / "LATEST.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return {**summary, "possible_contradictions": len(contradictions)}
