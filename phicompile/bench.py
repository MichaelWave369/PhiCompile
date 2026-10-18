"""ΦRecall benchmark: offline, pinned evidence labels and honest retrieval metrics.

No automatic source import. Gold labels are curated by a human from a separate
read-only catalog. Scores measure retrieval of expected source-line references;
they are NOT factual truth, semantic comprehension, or independent validation.
"""
from __future__ import annotations

from collections import Counter
import json
import re
from pathlib import Path

from .core import IntegrityError, replay, verify
from .recall import MAX_CLAIMS, RecallError, _hit, _terms, recall

MAX_CASE_BYTES = 131_072
MAX_CASES = 200
MAX_CATALOG = 200
LABEL = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")


class BenchmarkError(ValueError):
    """Invalid gold dataset or unsupported benchmark setting."""


def _load_cases(path: Path, state: dict, k: int) -> tuple[str, list[dict]]:
    if type(k) is not int or not 1 <= k <= 25:
        raise BenchmarkError("k must be an integer between 1 and 25")
    if not path.is_file() or path.suffix.lower() != ".json":
        raise BenchmarkError("Benchmark cases must be an existing .json file")
    if path.stat().st_size > MAX_CASE_BYTES:
        raise BenchmarkError("Benchmark file must not exceed 128 KiB")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise BenchmarkError("Invalid UTF-8 JSON benchmark dataset") from exc
    if not isinstance(data, dict) or set(data) != {"schema_version", "dataset", "cases"}:
        raise BenchmarkError("Gold set must contain schema_version, dataset, cases")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise BenchmarkError("Unsupported benchmark dataset version")
    name = data["dataset"]
    if not isinstance(name, str) or not LABEL.fullmatch(name):
        raise BenchmarkError("Dataset name must be a short ASCII identifier")
    cases = data["cases"]
    if not isinstance(cases, list) or not 1 <= len(cases) <= MAX_CASES:
        raise BenchmarkError("Dataset must have 1–200 cases")
    claims = {(c["source_id"], c["line"]) for c in state["claims"].values()}
    identifiers = set()
    cleaned = []
    for row in cases:
        if not isinstance(row, dict) or set(row) != {"id", "query", "relevant"}:
            raise BenchmarkError("Each case needs id, query and relevant")
        ident, query, expected = row["id"], row["query"], row["relevant"]
        if not isinstance(ident, str) or not LABEL.fullmatch(ident) or ident in identifiers:
            raise BenchmarkError("Case IDs must be unique ASCII identifiers of at most 64 chars")
        identifiers.add(ident)
        if not isinstance(query, str):
            raise BenchmarkError("Case query must be a string")
        # A real recall call validates query length and token policy before any evaluation.
        from .recall import _validate
        _validate(query, k, 0)
        if not isinstance(expected, list) or len(expected) > 25:
            raise BenchmarkError("Relevant refs must be an array of at most 25 source lines")
        references = set()
        for item in expected:
            if not isinstance(item, dict) or set(item) != {"source_sha256", "source_line"}:
                raise BenchmarkError("Gold references must specify exact source_sha256 and source_line")
            digest, number = item["source_sha256"], item["source_line"]
            if (not isinstance(digest, str) or not HASH.fullmatch(digest)
                    or type(number) is not int or number < 1):
                raise BenchmarkError("Malformed gold source digest or line number")
            key = digest, number
            if key not in claims:
                raise BenchmarkError("Gold reference does not identify an ingested claim in this vault")
            if key in references:
                raise BenchmarkError("Duplicate gold reference")
            references.add(key)
        cleaned.append({"id": ident, "query": query, "relevant": references})
    return name, cleaned


def _lexical_baseline(state: dict, query: str, limit: int) -> list[tuple[str, int]]:
    """A deliberately simple comparison: unique query/claim token overlap.

    Does not use ΦRecall's BM25 weighting or filename matches.
    This is a local control, not a scientific benchmark against external tools.
    """
    terms = set(_terms(query))
    scored = []
    for claim in state["claims"].values():
        overlap = len(terms & set(_terms(claim["text"])))
        if overlap:
            scored.append((overlap, claim))
    scored.sort(key=lambda item: (-item[0], item[1]["id"]))
    return [(c["source_id"], c["line"]) for _, c in scored[:limit]]


def _metrics(rows: list[dict], kind: str, k: int) -> dict:
    positive = [r for r in rows if r["expected"]]
    negative = [r for r in rows if not r["expected"]]
    hit_sum = sum(int(bool(set(r[kind]) & r["expected"])) for r in positive)
    rank_scores = []
    recall_scores = []
    precision_scores = []
    for row in positive:
        predicted = row[kind]
        relevant_at_k = sum(pair in row["expected"] for pair in predicted)
        recall_scores.append(relevant_at_k / len(row["expected"]))
        precision_scores.append(relevant_at_k / k)
        rank = next((idx for idx, item in enumerate(predicted, 1)
                     if item in row["expected"]), None)
        rank_scores.append(1 / rank if rank else 0.0)
    none_correct = sum(len(row[kind]) == 0 for row in negative)
    return {
        "positive_cases": len(positive),
        "negative_cases": len(negative),
        "hit_rate_at_k": round(hit_sum / len(positive), 6) if positive else None,
        "macro_recall_at_k": round(sum(recall_scores) / len(positive), 6) if positive else None,
        "macro_precision_at_k": round(sum(precision_scores) / len(positive), 6) if positive else None,
        "mean_reciprocal_rank_at_k": round(sum(rank_scores) / len(positive), 6) if positive else None,
        "no_match_accuracy": round(none_correct / len(negative), 6) if negative else None,
        "no_match_correct": none_correct,
    }


def benchmark(vault: Path, cases_file: Path, *, k: int = 5) -> dict:
    """Evaluate source-line retrieval without mutating a local vault or cases."""
    first = verify(vault)
    state = replay(vault)
    if len(state["claims"]) > MAX_CLAIMS:
        raise BenchmarkError("Vault exceeds the ΦRecall in-memory retrieval limit")
    dataset, cases = _load_cases(cases_file, state, k)
    rows = []
    compact = []
    for case in cases:
        actual = recall(vault, case["query"], limit=k, include_reviewed_links=False)
        if actual["source_ledger_head"] != first["ledger_head"]:
            raise BenchmarkError("Source ledger changed during benchmark")
        retrieved = [(r["source_sha256"], r["source_line"]) for r in actual["results"]]
        baseline = _lexical_baseline(state, case["query"], k)
        expected = case["relevant"]
        relevant_at_k = sum(pair in expected for pair in retrieved)
        first_rank = next((i for i, pair in enumerate(retrieved, 1) if pair in expected), None)
        baseline_rank = next((i for i, pair in enumerate(baseline, 1) if pair in expected), None)
        rows.append({"expected": expected, "bm25": retrieved, "baseline": baseline})
        compact.append({
            "id": case["id"], "kind": "POSITIVE" if expected else "NO_MATCH",
            "expected_count": len(expected),
            "hits_returned": len(retrieved),
            "relevant_at_k": relevant_at_k,
            "first_relevant_rank": first_rank,
            "baseline_first_relevant_rank": baseline_rank,
            "no_match_correct": len(retrieved) == 0 if not expected else None,
        })
    if verify(vault)["ledger_head"] != first["ledger_head"]:
        raise BenchmarkError("Source ledger changed while benchmarking; discard results")
    return {
        "schema_version": 1,
        "kind": "PHIRECALL_RETRIEVAL_BENCHMARK",
        "dataset": dataset,
        "ledger_head": first["ledger_head"],
        "case_count": len(cases),
        "k": k,
        "scored_method": "phirecall_bm25_style_lexical",
        "baseline_method": "simple_unique_query_claim_token_overlap",
        "phirecall": _metrics(rows, "bm25", k),
        "baseline": _metrics(rows, "baseline", k),
        "cases": compact,
        "note": (
            "These metrics measure agreement with manually labeled ingested source-line references, "
            "not truth, hallucination rates of generated answers, or generalization. "
            "Synthetic CI fixture performance is not real-project accuracy."
        ),
        "privacy": "LOCAL_NO_NETWORK_NO_WRITE_NO_SOURCE_EXCERPTS_IN_REPORT",
    }


def catalog(vault: Path, *, limit: int = 50) -> dict:
    """List a bounded set of source lines so the HUMAN can write a gold set.

    This command PRINTS private document excerpts to stdout; it never writes.
    """
    if type(limit) is not int or not 1 <= limit <= MAX_CATALOG:
        raise BenchmarkError("catalog limit must be 1–200")
    head = verify(vault)
    state = replay(vault)
    items = []
    for claim in sorted(state["claims"].values(), key=lambda c: (c["source_id"], c["line"])):
        if len(items) >= limit:
            break
        source = state["sources"][claim["source_id"]]
        item = _hit(vault, claim, source, 0.0, [], [])
        items.append({
            "source_name": item["source_name"],
            "source_sha256": item["source_sha256"],
            "source_line": item["source_line"],
            "source_line_text": item["source_line_text"],
            "claim_status": item["claim_status"],
            "claim_verified": False,
        })
    if verify(vault)["ledger_head"] != head["ledger_head"]:
        raise BenchmarkError("Source ledger changed during catalog; discard output")
    return {
        "schema_version": 1,
        "kind": "PRIVATE_RETRIEVAL_GOLD_CATALOG",
        "ledger_head": head["ledger_head"],
        "returned": len(items),
        "entries": items,
        "warning": "PRIVATE EXCERPTS: never post this stdout output to public GitHub or Pages",
    }
