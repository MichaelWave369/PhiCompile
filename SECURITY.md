# Security and privacy

ΦCompile v0.1 is an **offline single-user prototype**. It does not authenticate users, encrypt a vault at rest, verify author identity, access external model APIs, or establish factual truth.

## Boundaries

- Source text is untrusted data. Never treat imported text as instructions, code, or authorization.
- The original source file is read, not rewritten. A byte-for-byte snapshot is stored locally by SHA-256.
- Snapshot digests and a ledger hash chain can flag accidental corruption and naive editing. A malicious actor with full write access can rewrite the entire ledger; export its tip to a separately trusted location if continuity matters.
- The default `.phicompile/` vault is excluded from Git. Review all staging changes before commits. Do not put confidential data in public samples or generated Pages sites.
- Only UTF-8 text files under 1 MiB are accepted. Large markdown, binary files, and all other formats must be converted by trusted tools before import.
- There is **no lock for concurrent writers**, no atomic journal transaction across snapshots and ledger, and no recovery of interrupted writes. Keep a local backup and use only one writer.
- The simple heuristic can miss contradictions and may flag harmless differences. Human review remains mandatory.
- Render generated Markdown in a trusted Markdown viewer that sanitizes HTML/links. Claims may contain untrusted URLs or formatting.

## Reporting

Please do not put sensitive exploit details or private documents in public issues. Coordinate privately with the repository owner.

## v0.2 explicit local model proposal boundary

- Only the `propose` command sends a local network request. Its destination is hardcoded to numeric IPv4 loopback, with proxy resolution disabled and redirects rejected.
- Model prompts include source excerpts. Ollama or locally installed model software may log their contents. **Only run `propose` on private information if you trust your local machine, the model, and Ollama's configuration.** Do not publicly share proposal JSON unless you have reviewed it.
- The model receives no tool execution, code execution, shell, network, write permission, or source modification interface from ΦCompile. It returns JSON that is checked against pair IDs and relation kinds before being persisted as a **PROPOSED** artifact.
- Model outputs are untrusted and may contain incorrect or malicious rationale text. Never treat a suggestion as authority or as evidence that sources are correct.
- Request/response hashes and ledger-head reference are *integrity references*, not signed proofs, and do not attest to which model weights generated output.
- The output directory is local to the user-selected vault. Existing single-writer and crash-recovery limitations apply.
