# ΦCompile

**Build outward. Circle back. Compile forward.**

ΦCompile is an original, local-first prototype for **evidence-governed knowledge compilation**. It keeps unchanged source snapshots, extracts conservative candidate claims, links related claims across sources, flags possible contradictions, and creates a human-readable wiki plus an auditable receipt.

> **v0.1.0 is an experimental, deterministic proof of concept**, not a factual truth engine, autonomous research agent, or LLM-powered synthesizer. Candidate claims are always `INFERRED`; sources default to `UNKNOWN`. A flag does not establish that two statements actually contradict one another.

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

Treat imported text as *untrusted data*, never model instructions. No code or shell commands from source files are executed. This version does **not** make network requests or invoke Ollama automatically. Hash chaining is tamper-evidence, **not** signed identity, tamper-proof storage, or independent factual verification.

Supported imports: UTF-8 `.md` and `.txt`, maximum 1 MiB and 500 non-heading line candidates per file. The relation detector is deliberately narrow; false positives and missed contradictions are expected. No multi-writer concurrency or partial-write recovery guarantee yet.

## Design principles

1. **Ledger Above Ego:** evidence and revision history outrank model confidence.
2. **Human authority:** promotion, integration, publication, and execution require explicit approval.
3. **Provenance separation:** `OBSERVED`, `VERIFIED`, `INFERRED`, `DREAMED`, `SIMULATED`, and `UNKNOWN` are source-origin labels, not proof that source claims are true.
4. **Local first:** source bytes stay in a user-selected local vault; no cloud account required.
5. **Independent implementation:** no third-party project source code copied or forked.

## Roadmap

- **v0.1:** content-addressed immutable snapshots; conservative candidate claims; cross-source candidate links; hash-chain receipts; generated wiki; automated tests.
- **v0.2 (proposed):** governed local Ollama extraction adapter; claim-level provenance policy; independent contradiction review; model/version receipt.
- **v0.3 (proposed):** incremental dependency graph, source retractions/supersession, transactional commit/recovery, benchmark against retrieval-only baselines.
- **Later (not implemented):** optional read-only integrations with BrainC, Super Φ.Vessel, NBG, and Anti-M; a GitHub Pages demo using **synthetic fixtures only**.

See [Architecture](docs/ARCHITECTURE.md) and [Security](SECURITY.md).

**License:** MIT. Copyright 2026 MichaelWave369.
