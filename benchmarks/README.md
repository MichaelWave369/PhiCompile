# ΦRecall evaluation protocol

**Status:** v0.7 offline, original, deterministic proof of concept.

Five public, fictional Markdown documents and ten manually labeled questions are included. Eight questions target specific original source SHA-256 and line references. Two deliberately unanswerable questions test strict no-match behavior. None of these are genuine research findings or project records.

## Reproduce the synthetic benchmark

From the repository root:

```bash
python -m phicompile --vault .benchmark-fixture init
python -m phicompile --vault .benchmark-fixture ingest benchmarks/fixtures/memory.md --origin SIMULATED
python -m phicompile --vault .benchmark-fixture ingest benchmarks/fixtures/review.md --origin SIMULATED
python -m phicompile --vault .benchmark-fixture ingest benchmarks/fixtures/models.md --origin SIMULATED
python -m phicompile --vault .benchmark-fixture ingest benchmarks/fixtures/geometry.md --origin SIMULATED
python -m phicompile --vault .benchmark-fixture ingest benchmarks/fixtures/routing.md --origin SIMULATED
python -m phicompile --vault .benchmark-fixture bench --cases benchmarks/fixtures/gold.json --k 3
```

The benchmark fixture vault is locally generated, ignored by Git and should never be published. A green result on these fictional fixtures cannot prove performance on real documents.

## Opt-in real local benchmarks

1. Pick a handful of your own Markdown/text documents, and copy them to a separate evaluation workspace without changing the originals.
2. Import those local files to a private ΦCompile vault using normal `ingest`. Do not enable any cloud upload or public site export.
3. Run `python -m phicompile --vault .private-eval bench-catalog --limit 100`. This prints PRIVATE source excerpts, exact source hash values and line numbers to standard output.
4. Manually write a private JSON file containing at least 15–30 held-out search questions, each linked to every genuinely relevant ingested source line. Include deliberately unanswerable questions using `"relevant": []`.
5. Use the following case shape, replacing the placeholder hash with the actual catalog value:

```json
{
  "schema_version": 1,
  "dataset": "my_private_benchmark",
  "cases": [
    {
      "id": "question_001",
      "query": "source revision history",
      "relevant": [{"source_sha256": "INSERT_REAL_64_CHARACTER_DIGEST", "source_line": 2}]
    },
    {"id": "absent_001", "query": "a topic absent from the corpus", "relevant": []}
  ]
}
```

6. Run `python -m phicompile --vault .private-eval bench --cases private-gold.json --k 5`. The CLI does **not** save outputs. Record dataset version and returned ledger head when manually comparing runs.
7. Keep test questions genuinely held-out before tuning weights; don't grade retrieval on its own preferred result list.

## Metrics

- **Hit-rate@k**: share of positive cases retrieving at least one labeled source line.
- **Macro recall@k**: average fraction of each case's labeled relevant lines retrieved.
- **Macro precision@k**: average labeled hits divided by k, counting unused result slots as misses.
- **MRR@k**: average reciprocal first relevant rank in positive cases.
- **No-match accuracy**: fraction of negative cases with no returned candidates at all.
- **null** means that metric's positive or negative category had zero cases. Never treat null as perfect accuracy.

The scores measure agreement with human-curated relevance labels, not whether any retrieved assertion is factually true. Reviewer identity, semantic/vector search, retractions and production readiness are outside this version's scope.
