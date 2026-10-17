# Architecture and acceptance contract

## Current implemented contract: v0.1

**Input:** local UTF-8 `.txt` or `.md`, ≤1 MiB; at most 500 candidate lines. `--origin` is a provenance *description of the source*, not a truth claim.

**Raw store:** content-addressed `sources/<sha256>.txt` inside a user-chosen vault. A repeated byte-identical source does not append a ledger event; original input stays in place.

**Compiler:** extracts non-heading lines of length 12–480 into `INFERRED` candidate claims tied to exact source SHA and line. Cross-source `RELATED` and `POSSIBLE_CONTRADICTION` relations use intentionally conservative lexical matching. Neither kind is an epistemic promotion.

**Ledger:** `ledger.jsonl` contains INGEST events. Every event includes `prev_hash`, and its own SHA-256 over canonical JSON. `verify` replays the ledger and checks archived source digests. This detects modifications but cannot prove authorship or prevent rewriting all history.

**Derived output:** `wiki/INDEX.md`, per-claim Markdown, and `output/LATEST.md`. Generated knowledge is a projection of evidence, not a substitute for the evidence. Compilation doesn't modify originals, snapshots, or the event ledger.

## Workflow

1. **Ingest** a local sample using explicit source origin. A source is never promoted simply because it was read.
2. **Verify** all ledger links and snapshots.
3. **Compile** view artifacts and inspect proposed links and contradiction flags.
4. **Review** conclusions as a human before acting on them or integrating them anywhere.

## Acceptance checks

- Re-ingesting identical content does not create another event.
- Altering a stored source or any ledger event makes verification fail.
- Every generated claim links to its archived source SHA and line.
- Simple `is` vs `is not` opposites across two sources trigger a possible contradiction.
- No candidate is automatically labeled VERIFIED.
- Inputs containing apparent commands are copied as text without execution.
- An empty vault compiles with zero claims and a readable receipt.

## Future staged adapters (not implemented)

- **ΦIngest:** explicit connectors and a policy for potentially sensitive/private data.
- **ΦSynthesize:** optional Ollama model adapter produces proposals with extractive evidence spans; never accepts source instructions as tool permissions.
- **ΦLedger / NBG:** immutable provenance, review actions, model versions, replay and external signing.
- **ΦGraph:** content-addressed DAG with efficient invalidation, superseding and retracting claims, source/claim aliases and citations.
- **ΦRecall:** evidence-backed read-only query contract for BrainC/Vessie/Anti-M.
- **BudgetGenius:** local-first caching, timeouts, and spend/compute ceilings.

Before release, evaluate against a retrieval-only baseline using held-out questions, deliberate contradictory documents, false-fact injection, prompt-injection attempts, and source deletion/retraction scenarios. Do not present synthetic sample results as validated research.

## v0.2 local intelligence proposal bridge

The model-enabled path is intentionally separate from ingestion:

1. `plan` verifies existing source snapshots and ledger continuity and previews at most 16 possible cross-source claim pairs. It never invokes Ollama.
2. `propose` requires explicit invocation and a user-chosen installed model. It locally calls Ollama's `/api/generate` with a bounded JSON schema and without tool interfaces.
3. The response is validated against the exact pairs selected, limited relation labels and bounded rationale lengths. Any mismatch rejects the entire result.
4. The resulting file is an unverified content-hashed proposal under `output/proposals/`. It includes the source ledger head, stable claim/source/line references, requested and returned model names, request/response hashes, and optional inference metrics.
5. Source snapshots, `ledger.jsonl`, candidate claim statuses and compiled wiki files do not change during proposals. There is no auto-promotion or automatic downstream integration.

**Not guaranteed:** correctness of model reasoning, full coverage of candidate pairs, a model-weights cryptographic digest, signed identities, thread-safe concurrency, and independent factual verification.

Acceptance checks: no external endpoint; no request during `plan`; unknown IDs / malformed JSON / model mismatch rejected; no source or ledger mutations; model output never VERIFIED; CI runs with a fake transport, not a live model.
