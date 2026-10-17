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

## v0.3 ΦGraph browser isolation

- A graph contains sensitive source filenames, text excerpts, SHA identifiers and potential model proposals. Keep `.phicompile/output/graph/` in the local ignored vault; never serve or publish it publicly without reviewing and sanitizing your data.
- The self-contained HTML needs no server, external scripts, fetches, or tracking. The Content Security Policy blocks external connections and resources.
- The graph JSON embedded in HTML escapes HTML delimiter characters; the browser populates dynamic content via DOM `textContent` rather than HTML parsing. The bundled viewer can be audited directly in the repository.
- The graph viewer is a projection only; it does not write to the INGEST ledger or promote any candidate claim. Clicking archived sources uses relative local paths under the same vault, if the browser permits them.
- Local HTML is not encrypted and a person with access to your files can open it. Do not treat CSP or a hash chain as a sandbox for hostile local software.
