# AI project maintenance tracker

This is the master record for the daily modernization of the eight projects in this repository. Each run focuses on one project and aims to deliver a tested overhaul with revised documentation. A project is complete when its approved GitHub pull request has merged and the original local checkout has been verified against GitHub.

## Cadence and ownership

- Daily run: 09:00 America/Detroit, including weekends, beginning November 4, 2026. The first weekly maintenance batch remains recorded below.
- App automation: Daily AI project modernization (existing ID: weekly-ai-project-maintenance), continuing in the same Codex chat.
- Pending delivery: branch codex/maintenance-2026-11-02 contains independently reviewed 04/06 fixes and passing tests. GitHub CLI authentication is verified, but GitHub returned HTTP 500 for two push attempts on November 5. No PR or merge has occurred.
- Core roles: maintainer (PM and TPM), AI application engineer, and independent QA/reviewer.
- Specialists when needed: security and reliability, data science, and architecture/integrations.
- Use at most the available concurrency; start with the maintainer and up to three workers. Pass concise task context and coordinate ownership of shared files.
- Use one shared pass over current authoritative guidance and dependency advisories, then investigate technology-specific questions where they affect a proposed change.
- Routine failures return to the implementing engineer. After two unsuccessful repair attempts, reassess the approach and record any unresolved work; never mark an unverified fix complete.
- The maintainer owns this tracker. Parallel workers return evidence rather than independently editing it.

## Master progress chart

As of November 7, 2026: **0 of 8 overhauls synced**. Projects 01, 04, and 06 have fixes verified on local branches; project 01 documentation and dashboard work is committed. The chat progress view reflects this chart. See the [November 2 run report](docs/maintenance/2026-11-02.md) for evidence and limitations. Initial source baseline: November 1, 2026, commit bb425b76101e1c32caee3c4b823419ca49803720.

| Project | Overhaul stage | Main change or opportunity | Evidence | GitHub / local sync | Next action |
| --- | --- | --- | --- | --- | --- |
| 01 Customer Service Quality Audit | Ready locally · PR pending | Align dashboard score columns with the database model and provide runnable setup and batch guidance | Dashboard query regression 1 passed; compileall and diff check passed; Docker/PostgreSQL end-to-end unrun | Local branch codex/maintenance-2026-11-06-project-01; GitHub push pending | Publish after retrying GitHub's HTTP 500 failure; review hosted checks |
| 02 Procurement Contract Analyzer | Queued | Isolate uploads that currently share fixed temporary paths | Syntax passed; runtime baseline pending | No PR | Enforce upload limits and test concurrent PDF/DOCX requests |
| 03 Skills Graph Builder | Queued | Replace silent random-vector fallback with explicit provider failure | Syntax passed; runtime baseline pending | No PR | Verify deterministic recommendations and degraded behavior |
| 04 Meeting Note Analyzer | Queued · prior fix verified | Persistence helpers now flush IDs within the transaction | 6 tests passed; commit 3859152 | Prior fix: local only; GitHub server error blocked push | Publish prior fix, then address model errors and repeat analysis |
| 05 Research Report Writer | Queued | Replace placeholder search results with a source-backed provider interface | Syntax passed; runtime baseline pending | No PR | Verify source provenance and explicit fixture mode |
| 06 Banking Fraud Detection | Queued · prior fix verified | Actual account context and UTC event-time windows reach the alert policy | 17 tests passed; commits 3859152 and 3eba5be | Prior fix: local only; GitHub server error blocked push | Publish prior fix; evaluate calibration when labeled data is available |
| 07 Code Security Reviewer | Queued | Validate proposed fixes before labeling them safe | Syntax passed; runtime baseline pending | No PR | Add labeled fixtures and verify patch validation |
| 08 Sales QBR Builder | Queued | Run the graph once per QBR | Syntax passed; runtime baseline pending | No PR | Verify each stage runs once and produces a coherent trace |

## Overhaul queue

Initial order: **01 → 02 → 03 → 05 → 07 → 08 → 04 → 06**. A serious applicable advisory, failed check, or high-risk change can preempt the queue. Finish the active implementation before starting another by default. If a project is blocked by a dependency or decision, record the blocker and next action and move to the next actionable project. Work awaiting GitHub publication, CI, or merge approval remains visible and does not prevent an independent project from starting on a later day.

Before starting a new overhaul, check pending branches and PRs. Preserve and reuse prior work for 04 and 06 rather than duplicating it. While authentication is unavailable, independent work may still reach a reviewed local commit. If all eight projects are synced and there is no actionable follow-up, stay quiet and avoid cosmetic churn.

## Finding register

P1 indicates a major correctness or data-handling issue in the current prototype. Applicability and runtime impact must be confirmed before claiming production exposure.

| ID | Priority | State | Evidence | Acceptance check |
| --- | --- | --- | --- | --- |
| P01-001 | P1 | Locally fixed; end-to-end remains unverified | [Dashboard query](01.customer_service_quality_audit/dashboard/queries.py) and [score model](01.customer_service_quality_audit/db/db.py); branch codex/maintenance-2026-11-06-project-01 | Dashboard query reads schema-backed score columns and computes the overall mean; SQLite regression passes. Hosted PostgreSQL/API/dashboard flow remains to be verified |
| P02-001 | P1 | Open, static evidence | [Upload readers](02.procurement_contract_analyzer/app/utils/io.py) | Concurrent PDF/DOCX uploads cannot mix source text; oversized and corrupt files fail before model calls |
| P03-001 | P1 | Open, static evidence | [Embedding fallback](03.skills_graph_builder/src/services/utils.py) | Missing key, timeout, and rate limit produce explicit unavailable/degraded outcomes; deterministic fixtures retain stable rankings |
| P04-001 | P1 | Verified on local branch; not merged | [Database helpers](04.meeting_note_analyzer/db/db.py) and [API](04.meeting_note_analyzer/api/server.py); commit 3859152 | Passed: helper IDs, API POST/GET, batch linkage, and rollback on temporary PostgreSQL |
| P05-001 | P1 | Open, static evidence | [Search tool](05.research_report_writer/tools/web_search.py) | Configured live mode returns provider sources; fixture mode is explicit; missing configuration never fabricates research sources |
| P06-001 | P1 | Partially addressed on local branch; calibration open | [Transaction API](06.banking_fraud_detection/api/server.py) and [risk rules](06.banking_fraud_detection/tools/risk_calculator.py); commits 3859152 and 3eba5be | Passed: account context, preserved profile/status, user isolation, and persisted medium alert. Held-out policy evaluation remains outstanding |
| P07-001 | P1 | Open, static evidence | [Rewrite agent](07.code_security_reviewer/agents/code_rewriter_agent.py) | Invalid, unchanged, and behavior-breaking generated proposals cannot receive a validated-fix status |
| P08-001 | P1 | Open, static evidence | [QBR orchestrator](08.sales_qbr_builder/orchestrator/qbr_orchestrator.py) | Each fetch and generation stage runs once; recorded events and outputs use the same source snapshot |
| SHARED-001 | P1 | Partial: 04/06 installation and local regressions passed; CI authored | Per-project requirements, dev requirements, and focused CI workflow on maintenance branch | Unchanged 04/06 requirements installed on Python 3.12.16; 77-package environment is compatible; hosted CI and remaining project baselines are still pending |
| P06-002 | P1 | Open; unchanged by this batch | [Risk rules](06.banking_fraud_detection/tools/risk_calculator.py) | Calibrate aggregation and thresholds on labeled data; verify severity reachability, recall, and false-alert rates without simply lowering thresholds |
| P06-003 | P1 | Verified on local branch; not merged | New transaction_context.py and event-time tests in project 06; commit 3859152 | Passed: equivalent UTC instants, replay boundaries, and exclusion of current, future, and other-account events |

Additional backlog from the baseline: retry-safe ingestion and transcript retention (01); clause evidence and index reuse (02); weighted role requirements and import-time ingestion (03); typed model results and follow-up contract (04); citation grounding and failure propagation (05); severity calibration and timezone-safe replay (06); structural detection and persisted review details (07); revision feedback, versioned approvals, and export support (08).

## Run procedure

1. Read this tracker and applicable repository guidance. Check local and remote revisions, pending deliveries, and overlapping runs. Review repository-wide CI failures and changed dependencies for urgent issues; reserve deeper analysis for the focus project.
2. Pick one project. Diagnose its code, dependencies, tests, architecture, and docs against current primary sources and applicable advisories. Establish the installation, startup, and core-flow baseline in isolation. Set a realistic daily scope and concrete acceptance checks; carry over larger work without cutting verification.
3. Implement targeted improvements in an isolated branch or worktree. Delegate independent work with clear file ownership. Use disposable databases and deterministic provider fixtures. Paid provider evaluation requires an established test configuration and spending scope.
4. Revise the project README and any affected docs. Cover purpose, architecture/data flow, supported setup, configuration without secrets, a working example, test commands, and known limitations. Check the documented commands and examples against the implementation.
5. Have a fresh independent reviewer check the integrated code, docs, and test evidence. Rerun affected checks after review fixes. Record passed, failed, and unrun checks separately. A reviewed local commit is ready for publication when the scoped acceptance checks pass.
6. Push the verified branch and open or update one focused PR per overhaul when authentication permits. Preserve local commits on failure. Do not merge without user approval. After an approved merge, safely sync the original checkout and verify its revision matches GitHub without losing unrelated work.
7. Maintain the stage as **Queued → Diagnosing → Building & documenting → QA → Ready locally → PR open → Synced**. Record blockers separately; use **Merged · sync pending** when needed. Update the chart at meaningful transitions and record exact tests, main changes, branch/commit/PR links, blockers, and next action. Only count an overhaul as synced when both repositories are verified.
8. Keep this original workspace file as the working master. Publish a reconciled snapshot with an open maintenance PR where practical, or use one coordinated tracker PR if several project PRs are in flight. Compare against the latest local and GitHub versions before publishing or syncing so no newer rows are lost. Log fixes and references below; use the master chart as the source for the same-chat progress view.
9. End after one bounded batch. Show stage changes in this chat while a project is active and summarize completed work, changed blockers, and review links. Stay quiet on unchanged runs. Keep the existing daily automation as the single schedule.

## Completed fixes

These changes are verified in isolated local branches and have not been published or merged. Existing orphaned meeting rows are not repaired automatically. Fraud scoring weights and thresholds remain unchanged.

| Date | Project and finding | Main change | Verification | Commit and delivery |
| --- | --- | --- | --- | --- |
| 2026-11-02 | 04 / P04-001 | Flush generated parent/child IDs inside the transaction before callers use them | Original: 3 failed, 3 passed. Fixed: 6 passed against real temporary PostgreSQL, including API, batch, and rollback | 3859152; publication blocked, no PR |
| 2026-11-02 | 06 / P06-001 and P06-003 | Load real account context, preserve existing attributes, and use UTC event-time windows | Final: 17 passed; seeded anomaly yields the unchanged 71.5/medium policy and persists/retrieves its alert | 3859152 and 3eba5be; publication blocked, no PR |
| 2026-11-02 | Shared test foundation | Add focused PostgreSQL CI matrix for 04/06 with pinned action commits and no provider credentials | actionlint v1.7.12 passed; both suites also passed in TEST_DATABASE_URL mode. Hosted execution not run | 3859152; publication blocked, no PR |
| 2026-11-07 | 01 / P01-001 | Use database-backed score columns, calculate overall mean, add SQLite regression, protect Docker context from `.env`, repair quick-start and batch instructions | Dashboard query: 1 passed; Python compileall and `git diff --check` passed. Docker unavailable; full metrics discovery blocked by missing scikit-learn. Independent review caught and fixed a batch-copy instruction and Docker secret-context issue | codex/maintenance-2026-11-06-project-01; local commit pending |

## Run history

November 2 completed a verified local batch for 04/06. GitHub authentication is now verified, but pushes returned an internal server error twice on November 5. No PR or merge has occurred. The original checkout has not received application code.

| Date | Work completed | Verification | Next focus |
| --- | --- | --- | --- |
| 2026-11-01 | Read-only inventory and parallel static diagnosis; master tracker initialized | Source inspection; direct-dependency advisory lookup. No runtime tests or code fixes completed | 04 and 06 |
| 2026-11-02 | Checked all eight projects; implemented and independently reviewed scoped fixes for 04/06; added focused CI | 24 tests passed in total (01: 1, 04: 6, 06: 17); actionlint and dependency compatibility passed. 12 of 44 direct pins still match advisories requiring applicability review. GitHub authentication blocks publication | 01 and 02; first reconcile the pending maintenance branch |
| 2026-11-03 | Set up the daily single-project workflow and master progress chart; retained the November 2 branch and evidence | Schedule and tracker setup only; no new application fixes or tests | 01; reconcile pending 04/06 publication |
| 2026-11-06–07 | Diagnosed and fixed project 01 dashboard/database contract; revised setup and batch docs; added dashboard regression and Docker build-context protection; independent review completed | 1 targeted query test passed; compileall and diff check passed. Full environment and hosted checks not run. Local commit pending | 02; retry publishing 04/06 and 01 branches |

For each scheduled run, record the reviewed commit, focus project, checks passed/failed/not run, main changes, open PRs, blockers, and next actions. Record total agent tokens, model/provider costs, elapsed time to a reviewable PR, and repair rounds when available; use unavailable rather than estimated values when telemetry is missing.
