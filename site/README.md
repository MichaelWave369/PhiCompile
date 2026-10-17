# Public ΦCompile Field Lab

This directory contains a standalone React/Vite public exhibit intended for:

https://michaelwave369.github.io/PhiCompile/

**The exhibit contains only hand-authored fictional source records.** It does not ingest or display private knowledge, access the local vault, connect to Ollama, or communicate with the Python engine.

## Privacy and trust boundary

- Fixture data comes entirely from site/src/demo-data.mjs, marked SYNTHETIC_FIXTURE_ONLY.
- Examples mention project names for illustration, but are not claims about actual implementations, scientific findings, or repository state.
- There are no upload controls, input file readers, network calls to APIs, analytics scripts, or cloud model calls.
- Review accept/reject buttons modify in-memory React state only. They do not change real review ledgers and reset on reload.
- Simulated source codes and event IDs are NOT real SHA-256 receipts or verified provenance.
- All claims remain candidate assertions, not independently verified facts.

## Local use

Node 22+ recommended:

    cd site
    npm install
    npm test
    npm run dev
    npm run build

Production assets go into site/dist. The Vite base path is /PhiCompile/.

## GitHub Pages publication

The workflow at .github/workflows/public-field-lab.yml builds and tests this site for PRs. On main branch, it uploads ONLY site/dist and runs GitHub Pages deployment.

**Initial setup may be required:** GitHub repository Settings > Pages > Build and deployment > Source > GitHub Actions. A green build alone does not confirm the public website deployed.

Private PhiCompile artifacts remain only under the ignored .phicompile local vault, and are never read by this build workflow. Do not publish locally generated private graph HTML or JSON to Pages.

## Acceptance

- Synthetic data schema and source references pass the Node unit tests.
- React app builds to /PhiCompile/ assets.
- Interactive graph, inspector, filters, tab navigation, and review simulator work in-browser.
- Mobile presentation is responsive.
- Demo performs no runtime API requests.
- Public build contains no private vault documents.

**Ledger Above Ego.** Human review of a proposed relationship is never automatic verification of either underlying claim.
