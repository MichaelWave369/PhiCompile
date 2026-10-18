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

## v0.4 human review boundaries

- `review --decision accept` only approves a **relationship for local exploration**. It never asserts the truth of underlying claims or upgrades them to VERIFIED.
- Reviewer identity is user-supplied and not authenticated. Treat `--reviewer` as a label, **not proof of who reviewed**.
- `review` checks source snapshots, current ledger head, proposal receipt integrity, pair references, and prior decision chain **before** appending another decision event.
- Review events are hash-linked and append-only in intended operation, but not cryptographically signed or tamper-proof. An attacker with filesystem access can rewrite the history and recalculate hashes.
- All review notes are untrusted text. Graph output embeds them with HTML delimiter escaping and displays them using DOM textContent, never as executable commands.
- The prototype remains single-writer; do not run concurrent review or ingestion processes. Interrupted writes may require manual recovery from an offline backup.

## v0.6 retrieval safety boundary

PhiRecall never invokes Ollama, cloud APIs, or executable tools. It checks source snapshots, ledger event integrity, individual candidate IDs and exact archived source lines before returning evidence. It prints JSON to stdout and writes no files.

A source hit can reproduce private filenames and text. Only run this locally, and never publish private recall results via Pages or another shared surface. Recall scores rank lexical matches; they do not prove factual accuracy. A human-accepted relationship does not verify a claim.

Optional connection expansion validates model proposal receipts and human review history with the current evidence ledger head. Proposed, rejected or stale links are not traversed. It remains single-writer, unsigned, non-transactional prototype software.

## v0.7 private benchmark boundaries

- `bench` and `bench-catalog` never use models, network calls, or write to source evidence, review history or generated outputs. Both print JSON to standard output.
- Catalog output **does contain private original excerpts and filenames**. Never post it to public repositories, logs, or GitHub Pages.
- Benchmark summaries omit source excerpts and raw query strings. Avoid naming case IDs after secrets or sensitive documents.
- Gold references must identify currently ingested exact source hash/claim line pairs. Broken or stale targets fail rather than disappearing from the score.
- Retrieval performance is not a truth test. Synthetic-fixture metrics must not be described as accuracy on actual project archives.
