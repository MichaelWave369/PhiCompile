# ΦCompile

**Build outward. Circle back. Compile forward.**

ΦCompile is an original, local-first prototype for **evidence-governed knowledge compilation**. It keeps unchanged source snapshots, extracts conservative candidate claims, links related claims across sources, flags possible contradictions, and creates a human-readable wiki plus an auditable receipt.

> **v0.7.0 adds the ΦRecall benchmark lab:** independently labeled source-line targets, measured retrieval/no-match accuracy, and a simple lexical baseline. All runs remain local and read-only.

## Public React Field Lab (v0.5, synthetic exhibit)

The public [ΦCompile Field Lab](https://michaelwave369.github.io/PhiCompile/) is an interactive React/Vite visualization built from **fictional source records only**. This is not the private local engine: there is no vault access, backend connection, Ollama request, real research ingest, or cryptographic receipt generation. Demo review buttons only change temporary browser state, never real claim truth.

The site lives in [site/](site/README.md). GitHub Actions builds and checks the synthetic fixtures on pull requests, then attempts to deploy site/dist on main. For a first-time Pages setup, configure **Settings → Pages → Build and deployment → Source → GitHub Actions**. Passing tests does not imply Pages is already publicly accessible.

## ΦRecall: private source-backed retrieval (v0.6)

Run read-only search from the command line after ingesting sources:

    python -m phicompile --vault .phicompile recall "prototype ready" --limit 5
    python -m phicompile --vault .phicompile recall "provenance" --limit 8
    python -m phicompile --vault .phicompile recall "provenance" --include-reviewed-links --neighbors 5

Results are machine-readable JSON. Every match carries the exact archived source line, source name, origin metadata, original line number, SHA-256 snapshot identity, candidate claim ID, and explicit INFERRED / not-verified status. Distinguish terms matched in the claim from terms found only in a source filename. The simple deterministic BM25-style relevance score is **not** a probability or truth confidence.

Without matches, PhiRecall returns NO_MATCH rather than inventing an answer. Optional one-hop neighbor expansion follows only human-ACCEPTED connections on the *current* source ledger, after validating model proposal receipts and review history. Merely proposed, rejected and stale connections are excluded. Even reviewed links do not verify either claim.

Recall never calls Ollama or external APIs and never writes a file. **Its JSON output may contain confidential source excerpts**, so do not publish or redirect it into a public artifact. The implementation is an English-oriented lexical search, not semantic/vector retrieval, model-generated answers, factual verification, retraction/supersession handling or a completed BrainC/Super Phi.Vessel integration. It is a future read-only integration contract.

## ΦRecall benchmark lab (v0.7)

Before connecting ΦCompile to BrainC or Super Φ.Vessel, measure whether ΦRecall finds the expected source lines, not just whether it returns plausible text.

The new `bench` command scores ΦRecall against a separate human-labeled JSON file of **source SHA-256 + line number** targets. It compares the actual lexical ranker to a simple unique-token-overlap baseline and reports hit-rate@k, macro recall@k, macro precision@k, mean reciprocal rank@k, and no-match accuracy. Unrecognized or stale gold references fail explicitly.

Start with the safe synthetic fixtures (see [benchmark protocol](benchmarks/README.md)):

```bash
python -m phicompile --vault .phicompile ingest benchmarks/fixtures/memory.md --origin SIMULATED
python -m phicompile --vault .phicompile ingest benchmarks/fixtures/review.md --origin SIMULATED
python -m phicompile --vault .phicompile ingest benchmarks/fixtures/models.md --origin SIMULATED
python -m phicompile --vault .phicompile ingest benchmarks/fixtures/geometry.md --origin SIMULATED
python -m phicompile --vault .phicompile ingest benchmarks/fixtures/routing.md --origin SIMULATED
python -m phicompile --vault .phicompile bench --cases benchmarks/fixtures/gold.json --k 3
```

For **opt-in local project testing**, use a separate private vault and ingest copies of selected Markdown/text files without moving or modifying originals. Then run `bench-catalog --limit 100` locally to inspect source hashes, line numbers and private excerpts and manually label a private gold file. The catalog contains **private text** and should never be committed or uploaded. The benchmark result suppresses raw queries and original source excerpts by default. Neither command calls Ollama or other network APIs, writes files, or verifies factual assertions. Synthetic CI success does **not** establish real-project accuracy.

## Quick start

Requires Python 3.10+ and no runtime dependencies.

```bash
git clone https://github.com/MichaelWave369/PhiCompile.git
cd PhiCompile
python -m phicompile --vault .phicompile init
python -m phicompile --vault .phicompile ingest samples/example-a.md
python -m phicompile --vault .phicompile ingest samples/example-b.md
python -m phicompile --vault .phicompile verify
python -m phicompile --vault .phicompile compile
```

Then open `.phicompile/wiki/INDEX.md` and `.phicompile/output/LATEST.md`. The sample deliberately includes one contradictory statement so the possible-contradiction report can be tested.

Alternative installation: `python -m pip install -e .` followed by `phicompile --vault .phicompile ...`.

## Optional local Ollama proposals (v0.2)

With Ollama running on your **own PC** and a model already installed:

```bash
# Check which candidate pairs would be shared with the local model, without a network call:
python -m phicompile --vault .phicompile plan --max-pairs 8

# Explicitly ask a LOCAL Ollama model to suggest relationships:
python -m phicompile --vault .phicompile propose --model granite4.2:8b --max-pairs 8 --timeout 180
```

**Nothing runs automatically.** `propose` only connects to `http://127.0.0.1:11434/api/generate` and uses a structured JSON response with non-streaming, `think=false`, and `temperature=0`. It does not send requests to any public API. The model name is an example, not a bundled or automatically downloaded model.

Results are private, content-hashed **proposal receipts** at `.phicompile/output/proposals/proposal-<hash>.json`. Each links claims to source SHA-256 and line numbers, records the input ledger head, the requested/reported model, SHA-256 hashes of the request and response objects, and basic compute metrics when present.

**Proposal does not mean truth.** The model cannot edit sources, add a VERIFIED claim, update the source INGEST ledger, or publish/merge anything. Its output is strict-validated and stays `PROPOSED` until a separate, future human-reviewed workflow is designed.

Pair discovery is *not comprehensive*: it compares up to 24 recent claims against one another and up to 120 older claims, prioritizing lexical overlap, and submits at most 16 pairs. It can miss semantically related statements, subtle negations, and contradictions. The LLM still sees potentially malicious source text in the prompt; the safest boundary is its lack of execution tools and its read-only proposal output, **not** the strength of the prompt wording.

## ΦGraph: offline knowledge explorer (v0.3)

With two or more documents ingested (the synthetic samples work), run:

```bash
python -m phicompile --vault .phicompile graph
```

This writes a **private** self-contained graph viewer to `.phicompile/output/graph/index.html` and a machine-readable `graph.json` beside it. Open the HTML directly in a browser: no server, Ollama, account, CDN, or internet required. Explore the source / claim nodes, inspect source hashes and line numbers, filter possible contradictions, search, zoom, and pan.

Optional, only after explicitly running `propose` for your current ledger:

```bash
python -m phicompile --vault .phicompile graph --include-proposals
```

This opt-in view includes only locally stored proposal receipts whose content SHA-256 matches the filename, whose source ledger head is **current**, and whose cited claim IDs and source lines match the evidence ledger. Older receipts remain untouched and are counted as stale, but aren't displayed as live links. The model overlays are clearly marked **PROPOSED** rather than accepted knowledge.

**Privacy:** Graph files contain excerpts of your original sources. They are generated under `.phicompile/`, which Git ignores. **Never upload a private graph to GitHub Pages or commit it to a public repository.** This first view displays up to 650 nodes for performance, while its JSON exports all nodes under a bounded v0.3 cap. No silent edits to the ledger, source snapshots, or claim statuses.

## Governed human relationship review (v0.4)

Replace `REPLACE_WITH_64_CHARACTER_SHA256` with the SHA-256 printed by `propose`. Review a *particular model-suggested relationship* only after running `propose` on the current source ledger. The `propose` command prints a `proposal_sha256`; inspect its private JSON file to find the `pair_id` (usually `P001`, etc.).

```bash
# Show the current review history and verify decision hash-chain integrity:
python -m phicompile --vault .phicompile reviews

# Human reviewer deliberately ACCEPTS a connection for future exploration:
python -m phicompile --vault .phicompile review --receipt REPLACE_WITH_64_CHARACTER_SHA256 --pair-id P001 --decision accept --reviewer "Local reviewer" --reason "Both excerpts refer to the same feature under the same scope."

# Or REJECT it for a different scope or misleading inference:
python -m phicompile --vault .phicompile review --receipt REPLACE_WITH_64_CHARACTER_SHA256 --pair-id P001 --decision reject --reviewer "Local reviewer" --reason "The documents discuss different versions of the feature."

# View connection decisions alongside unreviewed AI suggestions:
python -m phicompile --vault .phicompile graph --include-proposals
```

Review results live in the ignored local `.phicompile/reviews/decisions.jsonl`. Each append-only event includes the full proposal receipt digest, stable pair ID / graph edge ID, source ledger head, user-supplied reviewer name, decision, written reason, and previous review hash. Newer reviews supersede earlier decisions **in the current view**, but the earlier events remain in history.

**CRUCIAL:** ACCEPT means "this *relationship* is useful/appropriate for a local knowledge graph." It does **not** mean either claim is factually correct, scientifically verified, source-authenticated, or authorized for execution. `VERIFIED` claim promotion is **not implemented**. The reviewer string is a **self-reported label**, not a login or signature. SHA chaining detects modifications but cannot prevent a person with full disk control from rewriting history.

When a new source is ingested, previous proposal receipts and decisions are still preserved, but the current graph excludes old-head suggestions and their reviews; generate a fresh proposal for the new ledger state if needed. This first review system is intentionally **single-writer**, without lock-based concurrency protection or transactional crash recovery.

## How it works

```text
input .md/.txt
    │ (read-only)
    ▼
content-addressed snapshot (sources/<sha256>.txt)
    │
    ▼
candidate claim extraction (line + original source hash)
    │
    ▼
cross-source relationships + POSSIBLE_CONTRADICTION flags
    │
    ▼
append-only INGEST event ledger (hash chained)
    │
    ▼
generated wiki/ and output/LATEST.md
```

- Every source byte is preserved in a content-addressed local snapshot. Originals are **never edited or moved**.
- Ingesting identical bytes again is a no-op.
- Claims carry a source hash, line number, and epistemic status. Status is **never automatically elevated to VERIFIED**.
- New claims are compared against previously compiled claims, so there is no repeated source extraction for unchanged inputs.
- The event ledger is hash-chained and checked before updates. The `verify` command also hashes all stored source snapshots.
- Derived pages are regenerated from the ledger and are **not** authoritative evidence.
- The local vault is ignored by Git. **Do not commit personal documents, source snapshots, or ledgers**.

## Trust boundaries

Treat imported text as *untrusted data*, never model instructions. No code or shell commands from source files are executed. The deterministic commands do **not** make network requests. The optional `propose` command makes **one explicitly requested local loopback request** to Ollama; it never runs automatically. Hash chaining is tamper-evidence, **not** signed identity, tamper-proof storage, or independent factual verification.

Supported imports: UTF-8 `.md` and `.txt`, maximum 1 MiB and 500 non-heading line candidates per file. The relation detector is deliberately narrow; false positives and missed contradictions are expected. No multi-writer concurrency or partial-write recovery guarantee yet.

## Design principles

1. **Ledger Above Ego:** evidence and revision history outrank model confidence.
2. **Human authority:** promotion, integration, publication, and execution require explicit approval.
3. **Provenance separation:** `OBSERVED`, `VERIFIED`, `INFERRED`, `DREAMED`, `SIMULATED`, and `UNKNOWN` are source-origin labels, not proof that source claims are true.
4. **Local first:** source bytes stay in a user-selected local vault; no cloud account required.
5. **Independent implementation:** no third-party project source code copied or forked.

## Roadmap

- **v0.1:** content-addressed immutable snapshots; conservative candidate claims; cross-source candidate links; hash-chain receipts; generated wiki; automated tests.
- **v0.2:** optional local Ollama relationship proposal bridge with strict output validation, model receipt, unchanged ingestion ledger, and automated mock-transport tests. Human promotion workflow and independently tested semantic extraction are **not** implemented.
- **v0.3:** offline local ΦGraph projection with source/claim nodes, line-traceable evidence edges, heuristic cross-source links, and opt-in SHA-checked current-head proposal overlays. **Not yet implemented:** retractions/supersession, incremental dependency invalidation, transaction recovery, retrieval-only benchmarking.
- **v0.4:** explicit human accept/reject relationship decisions, append-only hash-linked local review receipts, current-head validation, history-preserving override, and distinct reviewed edge styles in ΦGraph.
- **v0.6:** source-backed ΦRecall lexical retrieval, matched source-line excerpts, deterministic relevance, explicit no-match behavior and optional human-accepted one-hop link expansion. No model calls or source edits.
- **v0.7:** local retrieval benchmark with source-hash + line gold references, 10 synthetic test cases including no-match controls, reproducible rank/precision/recall metrics, simple independent lexical baseline and private-label catalog.
- **Later (not implemented):** genuine factual claim verification, reviewer signatures/authentication, incremental invalidation, crash-safe transactions, optional read-only integrations with BrainC, Super Φ.Vessel, NBG, and Anti-M; a **separate synthetic-fixture-only** GitHub Pages demo.

See [Architecture](docs/ARCHITECTURE.md) and [Security](SECURITY.md).

**License:** MIT. Copyright 2026 MichaelWave369.
