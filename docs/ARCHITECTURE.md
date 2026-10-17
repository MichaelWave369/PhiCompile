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

## v0.3 ΦGraph local projection

`graph` performs `verify` then replays the ledger, generating source nodes, claim nodes, `EVIDENCED_BY` edges, and deterministic `RELATED` / `POSSIBLE_CONTRADICTION` heuristic candidate edges. It writes reproducible `graph.json` and a self-contained `index.html` to the **ignored local vault**.

**Identity & meaning**
- Source node identity = full SHA-256 of preserved bytes; source origin is metadata about its origin, not a truth verdict.
- Claim node identity = full content-and-line-derived claim digest; all unverified extractions remain `INFERRED`.
- `EVIDENCED_BY` identifies a claim-to-source snapshot link, not proof of the claim's factual accuracy.
- `POSSIBLE_CONTRADICTION` is a flag, **not** an adjudication.
- When explicitly requested, model proposal edges originate only from valid content-hashed `PROPOSED` receipts with the **current** source ledger head. Any stale head is reported and not overlaid; altered hashes, missing claims, or source-line mismatch fail closed.

**Privacy & delivery**
No server, tracking, external font, cloud API, model execution, or third-party graph library. The entire graph data is embedded in a local HTML file with script-tag termination escaped. The viewer creates all untrusted source text elements through `textContent`, never `innerHTML`. No private graph is published automatically.

**Limits:** This is a read-only snapshot projection, not incremental dependency invalidation, a knowledge truth adjudicator, or a transactional/signed history system. The current viewer renders 650 nodes maximum for responsiveness; `graph.json` includes all eligible nodes up to export limits. Graph generation has the same one-writer limitations as v0.1.

## v0.4 human review, separate from factual verification

Reviewing a suggested connection requires explicit CLI input naming the content-hashed proposal receipt, its unique pair ID, a human-selected ACCEPT or REJECT decision, self-reported reviewer, and an explanatory reason.

- Reject missing, stale, modified, or non-matching model proposal receipts. Never accept a historical receipt from a superseded source ledger head into the current graph.
- Before append, verify the original source ledger, archived content digests, current proposal identities, and the separate review decision hash chain.
- Append a review event with SHA-256 hash over canonical event JSON, linked to the prior review event digest, including the source ledger head and stable graph edge ID.
- Never mutate the original source ledger, source snapshots, model proposal receipts, or claim status when reviewing a relationship.
- Repeated review of the same edge is permitted; the **latest** human decision is the effective current view, but every earlier review remains in the review ledger.
- ΦGraph still labels model suggestions as model-derived and shows a distinct `ACCEPTED_CONNECTION` or `REJECTED_CONNECTION` status, with an explanatory reviewer note. **Neither means VERIFIED.**
- Reviewer names are not authenticated or signed. Hash chaining is tamper-evidence against edits without chain re-computation, not defense against a compromised disk.

Validation cases: review twice and preserve both events; tamper original source, model receipt, or review chain and fail closed; reject unknown pair IDs and stale proposal ledgers; ensure `claim.status` always remains INFERRED.

## v0.6 PhiRecall extractive contract

The local read-only recall command emits a schema_version=1 JSON object with an EXTRACTIVE_EVIDENCE_RECALL kind, original query, current ledger head, MATCHES/NO_MATCH, and ranked source-backed candidate excerpts. Each result includes claim ID and INFERRED status, exact original archived source line and number, source hash and origin metadata, and a BM25-style relevance score. Source filename matches are separated from claim-text matches.

The retrieval implementation bounds query length to 256 characters, distinct terms to 16, returned matches to 25, and optional reviewed neighbors to 10. It scans at most 20,000 candidate claims in memory, verifies source snapshots and chain before searching, and reconstructs every matched claim ID and exact original source line. The ledger head is checked again before return.

Optional human-reviewed link expansion uses the verified current-head graph projection, traverses only ACCEPTED_CONNECTION relations, and includes the human review receipt hash plus source-backed neighbor excerpt. No source or review metadata is written; no LLM call takes place. Ranking is lexical rather than semantic, scores are not calibrated confidence, and results are neither generated answers nor evidence of factual truth.

Potential future integrations with BrainC or Super Phi.Vessel remain explicitly unimplemented.
