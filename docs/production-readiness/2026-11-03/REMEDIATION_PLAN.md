# EGOSHIELD remediation plan

This roadmap addresses [REVIEW.md](REVIEW.md); no tests, deployments or fixes were executed. Commands are future plans. Do not weaken existing tests or thresholds.

## Phases and dependencies

| Phase | Entry | Tasks | Exit |
|---|---|---|---|
| 0. Baseline | Owner approves isolated test environment and supported platforms | T1 | Reproductions and collected-test inventory recorded, including failures |
| 1. Correctness and trust | T1; owner selects local threat model | T2, T3 | Authorization, revocation and text restoration proven with negative tests |
| 2. Artifact and automation | T1; T2/T3 changes available | T4, T5 | Clean artifacts install/load and meaningful CI gates reject intentional breaks |
| 3. Operations and acceptance | T2–T5; owner supplies release/restore policy | T6, T7 | Restore, platform UX, security and independent acceptance evidence reviewed |

T2, T3 and T4 can start after T1; T5 integrates their tests. T6 depends on working artifacts and security decisions. T7 follows all earlier tasks.

## T1 — Establish a reproducible baseline

**Links:** EGO-02–EGO-05; preventive requirement for honest measurement. **Prerequisites:** pinned checkout, isolated machine, owner-approved browser and Python versions. **Observed paths:** `pyproject.toml`, `pytest.ini`, `tests/unit/test_plugins.py`, `tests/integration/__init__.py`, `extension/manifest.json`, `.github/workflows/ci.yml`.

1. Inventory interpreter and browser versions; inspect both pytest configurations and actual collection, including `__init__.py` modules.
2. In an isolated checkout, install approved development dependencies and run the planned `python -m pytest tests/ -v`; record collection, failures and skips.
3. Reproduce trust removal, failed writes, and annotate/dismiss with synthetic text; attempt installed entry point and unpacked extension load. Record observations and environment.

**Output:** baseline report with test IDs, failing behaviors and artifact results. **Verification:** a second reviewer can repeat each case on the pinned SHA. **DoD:** [ ] Collection and skips captured; [ ] failing reproductions or explicit blockers recorded; [ ] no real browsing data used.

## T2 — Authenticate the local API and bound requests

**Links:** EGO-01, EGO-06. **Prerequisites:** T1 and owner-approved same-user threat model, browser extension identity and credential provisioning. **Observed paths:** `egoshield/daemon/main.py`, `egoshield/daemon/api/routes.py`, `extension/js/background.js`; **proposed path:** `tests/integration/test_local_auth.py`.

1. Specify actors allowed to read history, analyze or modify rules/settings; choose OS-protected local capability or authenticated IPC. Origin, loopback and public extension ID are not credentials.
2. Authorize sensitive routes, compare exact origins, bound limits by authenticated identity, and enforce byte limits before processing. Define credential storage, rotation and revocation without a universal embedded secret.
3. Test valid, missing, incorrect and revoked credentials; hostile and missing origins, port-prefix lookalikes, changing client headers and oversized multibyte payloads. Verify the background-to-daemon path.

**Output:** documented trust contract and integrated protections. **Verification:** independently send unauthorized requests to history and settings and observe denial; intentionally bypass the gate to confirm tests fail. **DoD:** [ ] Sensitive operations require authorization; [ ] resource limits resist tested identity rotation; [ ] legitimate extension flow and rotation work.

## T3 — Correct trust state and page restoration

**Links:** EGO-02, EGO-03. **Prerequisites:** T1; API authorization contract from T2 for end-to-end acceptance. **Observed paths:** `extension/js/background.js`, `extension/js/content.js`, `egoshield/daemon/api/routes.py`; **proposed paths:** `tests/browser/`, `tests/integration/test_trust_rules.py`.

1. Make daemon rules authoritative; resolve rule IDs, delete on removal, commit local state only after acknowledgment, surface errors and reconcile after restart.
2. Restore only original matched text during cleanup; preserve unaffected text and DOM behavior.
3. Browser-test add, remove, restart, rejected writes and daemon disconnection; assert UI state and resumed analysis. Compare repeated annotation/dismiss cycles against the original DOM and test keyboard access.

**Output:** consistent trust lifecycle and non-destructive overlays. **Verification:** deliberately omit server deletion or restore `wrapper.textContent`; corresponding tests must fail. **DoD:** [ ] Revoked domain is analyzed after refresh; [ ] failed writes do not create false trust; [ ] dismissal restores original content.

## T4 — Make distribution artifacts usable

**Links:** EGO-04. **Prerequisites:** T1 and owner-selected distribution browsers. **Observed paths:** `pyproject.toml`, `extension/manifest.json`, `egoshield/daemon/db/schema.sql`; **proposed path:** `tests/packaging/`.

1. Align the console entry point and package data; inspect the wheel for SQL and dashboard resources.
2. Supply icons or remove references if supported; reconcile versions under an owner-chosen release scheme.
3. Build a wheel and extension bundle; install outside the checkout, invoke the installed command and load the bundle in supported browsers.

**Output:** reproducible wheel and extension bundle with asset inventory. **Verification:** smoke the installed command and extension-to-daemon handshake; remove an included asset or schema in a negative fixture to prove the artifact check detects it. **DoD:** [ ] Fresh install starts; [ ] all declared assets exist; [ ] browser load and handshake observed.

## T5 — Make automation meaningful and supply chain repeatable

**Links:** EGO-05 and preventive dependency integrity. **Prerequisites:** T1, T2–T4 test interfaces. **Observed paths:** `.github/workflows/ci.yml`, `requirements.txt`, `uv.lock`, `tests/unit/test_plugins.py`; **proposed path:** a documented CI test entry point.

1. Replace placeholder plugin assertions with actual loader rejection and allowed-loading tests; collect existing tests and report unexpected skips.
2. Add pytest, artifact smoke and browser/API gates; retain compilation separately. Define a maintained script if needed.
3. Choose an authoritative lock/install method for CI and release, pin actions and run an approved dependency audit with documented exceptions.

**Output:** repeatable CI with test and dependency evidence. **Verification:** deliberate broken authorization, trust removal and plugin directory protection each make their respective test fail; restore code and observe all intended checks. **DoD:** [ ] CI runs collected behavior tests; [ ] negative controls fail; [ ] dependency resolution and exceptions documented.

## T6 — Operational recovery and privacy

**Links:** preventive operations and data-protection requirements; EGO-01. **Prerequisites:** T2–T5 and owner approval of retention, release channels and backup policy. **Observed paths:** `egoshield/daemon/main.py`, `docs/security.md`, `docs/deployment.md`; **proposed path:** `docs/recovery-runbook.md`.

1. Trace synthetic content, domains, URL hashes and credentials through logs, SQLite, diagnostics and Ollama; document retention and redact sensitive paths.
2. Specify signing, upgrade/rollback, credential rotation and SQLite/WAL backup, schema compatibility and model-outage handling.
3. Back up during representative activity, restore separately, compare records and analyze; exercise failed upgrade and rollback without overwriting originals.

**Output:** privacy data map and observed recovery runbook. **Verification:** independent operator reproduces backup/restore and confirms restored rules and history, logs and retention with synthetic canaries. **DoD:** [ ] Restore evidence exists; [ ] sensitive-data handling is verified; [ ] release and rollback owner approves policy.

## T7 — Independent product acceptance

**Links:** all findings; preventive accessibility and detector-quality requirements. **Prerequisites:** T2–T6 complete, supported platform matrix and domain validation criteria approved. **Observed paths:** `extension/js/content.js`, `extension/js/background.js`, `docs/deployment.md`.

1. Have an independent reviewer rerun reproductions through installed artifacts, including denied requests and trust reversal.
2. Test keyboard, screen reader, contrast, failure messages and dismissal across browsers; evaluate false positives/negatives against an approved, consented corpus.
3. Inspect provenance, CI logs and restore observations; document failures and obtain a go/no-go decision. Green builds do not establish safety or detection quality.

**Output:** independent acceptance record and residual-risk decision. **Verification:** attach dated environment, artifact hashes, results and failed negative controls. **DoD:** [ ] Every finding is retested; [ ] accessibility and quality limits are disclosed; [ ] owner signs off or release remains blocked.

## Production acceptance and approval gates

- [ ] T2–T5 pass on release artifacts, not merely source checkout.
- [ ] T6 restore and T7 independent product checks have observed evidence; any open issues have named owners and deadlines.
- [ ] Owner approves trust model, privacy/retention, supported browsers, dependency exceptions, signing identities and release destination before changes to those policies.
- [ ] Rollback retains a verified pre-upgrade backup and prior signed artifacts; test schema compatibility before rollback and never overwrite the only backup. Stop release on failed authorization, trust revocation or restore; no publication is authorized by this plan.
