"""ΦRecall v0.6: offline, extractive, provenance-first retrieval.

No cloud, Ollama, network access, model-generated answers, filesystem writes,
or fact promotion. Every hit points to a byte-verified snapshot and exact line.
"""
from __future__ import annotations

from collections import Counter
import math
import re
from pathlib import Path

from .core import IntegrityError, replay, sha, verify

MAX_QUERY_CHARS = 256
MAX_QUERY_TERMS = 16
MAX_CLAIMS = 20000
MAX_RESULTS = 25
MAX_NEIGHBORS = 10
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
TERM_PATTERN = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset((
    "the", "and", "for", "with", "from", "that", "this",
    "have", "has", "are", "was", "were", "not", "into",
    "about", "will", "can", "its", "what", "where", "which",
    "when", "who", "how", "does", "did", "could", "would",
    "should", "there", "their", "then", "them", "your",
))


class RecallError(ValueError):
    """Unsupported, ambiguous, or integrity-invalid retrieval request."""


def _terms(text: str) -> list[str]:
    return [token for token in TERM_PATTERN.findall(text.casefold())
            if token not in STOPWORDS and len(token) > 1]


def _validate(query: str, limit: int, neighbors: int) -> list[str]:
    if not isinstance(query, str) or not 1 <= len(query.strip()) <= MAX_QUERY_CHARS:
        raise RecallError("Query must have 1–256 characters")
    if any(ord(character) < 32 or ord(character) == 127 for character in query):
        raise RecallError("Query cannot contain control characters")
    if type(limit) is not int or not 1 <= limit <= MAX_RESULTS:
        raise RecallError("Limit must be between 1 and 25")
    if type(neighbors) is not int or not 0 <= neighbors <= MAX_NEIGHBORS:
        raise RecallError("Reviewed-neighbor limit must be between 0 and 10")
    tokens = sorted(set(_terms(query)))
    if not tokens or len(tokens) > MAX_QUERY_TERMS:
        raise RecallError("Query must contain between 1 and 16 distinct searchable terms")
    return tokens


def _source_line(vault: Path, source_id: str, line: int, expected_claim: str) -> str:
    """Recheck source line against archived bytes, not the ledger alone."""
    if not isinstance(source_id, str) or not SHA256_PATTERN.fullmatch(source_id):
        raise IntegrityError("Malformed evidence SHA-256")
    if type(line) is not int or line < 1:
        raise IntegrityError("Malformed source line number")
    raw = (vault / "sources" / (source_id + ".txt")).read_bytes()
    if sha(raw) != source_id:
        raise IntegrityError("Source evidence hash changed during recall")
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise IntegrityError("Source is no longer UTF-8") from exc
    if line > len(lines):
        raise IntegrityError("Claim refers to missing source line")
    original = lines[line - 1]
    candidate = original.strip()
    if candidate.startswith(("- ", "* ")):
        candidate = candidate[2:].strip()
    if candidate != expected_claim:
        raise IntegrityError("Claim no longer matches its exact source line")
    return original


def _hit(vault: Path, claim: dict, source: dict, score: float,
         claim_matches: list[str], title_matches: list[str]) -> dict:
    claim_id = claim["id"]
    sid = claim["source_id"]
    line = claim["line"]
    if (not isinstance(claim_id, str) or not SHA256_PATTERN.fullmatch(claim_id)
            or claim["status"] != "INFERRED"
            or sha((sid + ":" + str(line) + ":" + claim["text"]).encode("utf-8")) != claim_id):
        raise IntegrityError("Claim identity or epistemic status invalid")
    original = _source_line(vault, sid, line, claim["text"])
    return {
        "claim_id": claim_id,
        "claim_status": "INFERRED",
        "claim_verified": False,
        "claim_text": claim["text"],
        "source_sha256": sid,
        "source_name": source["name"],
        "source_origin": source["origin"],
        "source_line": line,
        "source_line_text": original,
        "evidence_type": "EXACT_ARCHIVED_SOURCE_LINE",
        "relevance_score": round(score, 6),
        "matched_claim_terms": claim_matches,
        "matched_source_title_terms": title_matches,
    }


def recall(vault: Path, query: str, *, limit: int = 8,
           include_reviewed_links: bool = False, neighbors: int = 5) -> dict:
    """Return ranked, cited candidate excerpts. Results are NOT answers or truth.

    Optional one-hop expansion uses only current-head, human-ACCEPTED links
    to trace adjacent excerpts; rejected/merely proposed relations are excluded.
    """
    tokens = _validate(query, limit, neighbors)
    if type(include_reviewed_links) is not bool:
        raise RecallError("include_reviewed_links must be boolean")
    first = verify(vault)
    state = replay(vault)
    if len(state["claims"]) > MAX_CLAIMS:
        raise RecallError("Vault exceeds v0.6 in-memory retrieval limit")
    claims = sorted(state["claims"].values(), key=lambda c: c["id"])
    docs = []
    frequencies = Counter()
    total_length = 0
    for claim in claims:
        source = state["sources"].get(claim["source_id"])
        if not source:
            raise IntegrityError("Orphaned source pointer")
        text_terms = _terms(claim["text"])
        title_terms = _terms(source["name"])
        counts = Counter(text_terms)
        titles = Counter(title_terms)
        # Source title is navigation metadata, not claim evidence.
        weighted = counts + Counter({k: 2 * v for k, v in titles.items()})
        length = sum(weighted.values())
        docs.append((claim, source, counts, titles, weighted, length))
        frequencies.update(set(weighted))
        total_length += length
    avg_len = total_length / max(1, len(docs))
    n_docs = len(docs)
    scored = []
    for claim, source, counts, titles, weighted, length in docs:
        claim_matches = sorted(set(tokens) & set(counts))
        title_matches = sorted(set(tokens) & set(titles))
        if not claim_matches and not title_matches:
            continue
        score = 0.0
        for term in tokens:
            freq = weighted.get(term, 0)
            if freq == 0:
                continue
            idf = math.log(1 + (n_docs - frequencies[term] + 0.5)
                           / (frequencies[term] + 0.5))
            score += idf * (freq * 2.2) / (
                freq + 1.2 * (0.25 + 0.75 * length / max(avg_len, 1))
            )
        scored.append((score, claim, source, claim_matches, title_matches))
    scored.sort(key=lambda item: (-item[0], item[1]["id"]))
    ranked = [
        _hit(vault, c, s, score, cterms, tterms)
        for score, c, s, cterms, tterms in scored[:limit]
    ]
    related: list[dict] = []
    if include_reviewed_links and neighbors and ranked:
        # Graph overlay verifies current-head model receipts and review history.
        from .graph import build_graph
        graph = build_graph(vault, include_proposals=True)
        if graph["ledger_head"] != first["ledger_head"]:
            raise RecallError("Ledger changed while preparing retrieval context")
        seed_ids = {"claim:" + item["claim_id"] for item in ranked}
        already = {item["claim_id"] for item in ranked}
        used = set()
        for edge in graph["links"]:
            if edge["status"] != "ACCEPTED_CONNECTION":
                continue
            a, b = edge["from"], edge["to"]
            if a in seed_ids and b not in seed_ids:
                other, via = b, a
            elif b in seed_ids and a not in seed_ids:
                other, via = a, b
            else:
                continue
            if not other.startswith("claim:") or not via.startswith("claim:"):
                raise IntegrityError("Reviewed connection references a non-claim")
            other_id = other.removeprefix("claim:")
            if other_id in already or other_id in used:
                continue
            claim = state["claims"].get(other_id)
            if claim is None:
                raise IntegrityError("Reviewed connection refers to missing evidence")
            source = state["sources"].get(claim["source_id"])
            if source is None:
                raise IntegrityError("Reviewed connection refers to missing source")
            neighbor = _hit(vault, claim, source, 0.0, [], [])
            related.append({
                "via_claim_id": via.removeprefix("claim:"),
                "link_kind": edge["kind"],
                "link_status": "ACCEPTED_CONNECTION",
                "relationship_review_hash": edge["review_hash"],
                "proposal_receipt_sha256": edge["receipt_sha256"],
                "review_reason": edge["review_reason"],
                "not_factual_verification": True,
                "evidence": neighbor,
            })
            used.add(other_id)
            if len(related) >= neighbors:
                break
    last = verify(vault)
    if last["ledger_head"] != first["ledger_head"]:
        raise RecallError("Ledger changed during retrieval; results discarded")
    return {
        "schema_version": 1,
        "kind": "EXTRACTIVE_EVIDENCE_RECALL",
        "query": query,
        "query_terms": tokens,
        "source_ledger_head": first["ledger_head"],
        "status": "MATCHES" if ranked else "NO_MATCH",
        "truth_notice": "Source matches are NOT evidence that assertions are factually true. Reviewed links do not verify claims.",
        "ranking": "deterministic_bm25_lexical_not_calibrated_confidence",
        "claims_scanned": n_docs,
        "returned": len(ranked),
        "results": ranked,
        "reviewed_connections_enabled": include_reviewed_links,
        "related_reviewed_connections": related,
        "privacy": "LOCAL_READ_ONLY_NO_NETWORK_NO_STORAGE",
    }
