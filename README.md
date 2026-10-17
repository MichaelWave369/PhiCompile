# ΦCompile

**Build outward. Circle back. Compile forward.**

ΦCompile is an original, local-first prototype for **evidence-governed knowledge compilation**. It keeps unchanged source snapshots, extracts conservative candidate claims, links related claims across sources, flags possible contradictions, and creates a human-readable wiki plus an auditable receipt.

> **v0.3.0 adds ΦGraph:** a deterministic, private, offline visualization of source evidence, candidate claims, and cross-source connections, with optional unverified model-proposal overlays. The source ledger remains authoritative for evidence, not truth; no model result is promoted to VERIFIED.

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
- **Later (not implemented):** optional read-only integrations with BrainC, Super Φ.Vessel, NBG, and Anti-M; a **separate synthetic-fixture-only** GitHub Pages demo.

See [Architecture](docs/ARCHITECTURE.md) and [Security](SECURITY.md).

**License:** MIT. Copyright 2026 MichaelWave369.
