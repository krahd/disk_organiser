# Durable Disk Organiser acceptance backlog

Updated: 2026-10-06. Release/commercial acceptance is held. Work remains iterative and includes core safety, organisation logic, experience and reliability. No main merge, release, deployment or Apple upload is included.

## P0: data safety and current repair

| ID | Outcome | Current state | Required evidence / stopping gate |
| --- | --- | --- | --- |
| SAFE-01 | Persisted metadata never becomes unchecked filesystem authority | Defensive schema repair implemented; independent confirmation pending | Pure corruption/schema tests cover every field, shape, identity relationship and derived name. Invalid records cause zero selected-folder I/O and are retained. A permitted reviewer confirms the boundary. |
| SAFE-02 | Only the exact freshly reviewed plan can authorise copy application | In-process digest implemented; UI integration pending | Restart, alteration, expiry and cache eviction require rescan. Whole-plan stale checks precede mutation. Repeated/uncertain requests never reapply an interrupted plan. Exact-head API and UI tests pass. |
| SAFE-03 | Recovery cannot remove an original or an uncertain file | Automatic removal disabled | Preserve all files and journals. Design an authentic ownership mechanism, original-source exclusion and crash-safe recovery protocol before re-enabling any removal. Independent confirmation required; a journal inode/hash claim is insufficient. |
| SAFE-04 | Unknown/old journals stay inspectable without execution or silent migration | Retained/blocked-record reporting implemented | Benign malformed/old-record fixtures remain byte-for-byte intact. User-visible explanation differentiates a safety hold from completed recovery. A deliberate safe export/inspection route is designed. |
| SAFE-05 | Local browser boundary prevents drive access through unrelated sites | Origin/Host, token and frame protections implemented; guided and legacy source mutations disabled by default | Same-origin/Host/CSRF/frame tests pass on current head. Review all retained legacy endpoints as part of the threat model. Never expose the service publicly. |
| SAFE-06 | Legacy interfaces cannot imply guided guarantees | Partial guard/label separation | Preserve backups/history. Complete a separate audit of legacy move, overwrite, undo and cleanup semantics before enabling them through default UX. |

## P1: sustained reliability and useful organisation

| ID | Outcome | Current state | Required evidence / stopping gate |
| --- | --- | --- | --- |
| REL-01 | Ordinary interruption, full disk, permissions and journal failure preserve source bytes | Synthetic coverage exists; broaden systematically | Bounded subprocess interruption and fault injection only in ordinary temporary fixtures. Compare original hashes before/after, retain partial outputs, and inspect restart states. Do not reproduce previously unsafe path-redirection operations. |
| REL-02 | Repeated operation/session lifecycle stays understandable | Partial; separate UX work active | Cancel-before-apply, reload, Back/Forward, double clicks, connection loss, history refresh and process restart have explicit expected states. No automatic retry or false completion. |
| REL-03 | Long-run bounded workload has stable resource use | Not established | Define workload sizes, time budget, disk budget and a stop condition; run only synthetic local app data. Record failures and reproducible seeds. A test count alone is not a soak result. |
| LOGIC-01 | Plans improve a real folder without pretending extension rules understand content | Basic closed extension mapping; separate pure Disk Model slice assigned | Build a pure policy/explanation layer, with explicit unknowns, supported intents and deterministic tests. Suggestions cannot choose arbitrary destinations or bypass core validation. |
| LOGIC-02 | Metadata and filename edge cases are accurately explained | Partial | Unicode/case behaviour, old timestamps, unusual legal filenames, unreadable entries and platform differences get bounded fixtures and clear unsupported reasons. No silent omission. |
| UX-01 | Users can inspect and understand exact effects and limits | Guided UI implemented; safety-state revision active | Readable desktop/mobile paths, non-zero byte display, skipped reasons, explicit scope and approval, disabled recovery and blocked-history messaging. Real synthetic runtime screenshots inspected on the integrated head. |
| UX-02 | Retained data can be reviewed without dangerous recovery actions | Not complete | Design and test a read-only report/export flow with privacy-aware path handling. Export does not establish deletion authority or permission to erase media. |
| PLATFORM-01 | macOS behaviour is verified on representative storage | Not established | Test ordinary local APFS fixtures on an authorised connected environment; document permissions, no-follow behaviour and durability bounds. No real user-volume mutation. |
| PLATFORM-02 | Windows has a truthful supported path | Guided operations unsupported | Preserve explicit refusal until a separately designed Windows-safe implementation and runtime evidence exist. Passing legacy tests is not Windows guided acceptance. |
| OFFLOAD-01 | Cross-volume verified media ingest is a real module | Not implemented | Source retention, per-destination verification, partial-failure reporting and durable manifests are required. Same-root classified copies do not satisfy this item. |
| PRIVACY-01 | Remote inference stays opt-in and unnecessary for the safe baseline | Guided surface local-only | Network-observation tests for guided runtime; no paths/content to services. Any future inference work needs an explicit data/recipient boundary and separate review. |
| DEPS-01 | Dependency repairs stay targeted and reproducible | Current audits clean | Recheck exact locks in CI after changes; test API compatibility of scoped overrides. Do not suppress findings or mass-upgrade without evidence. |

## Acceptance and iteration loop

1. Assign disjoint files and a concrete outcome; inspect the current head and existing findings.
2. Implement the smallest defensible increment. Fail closed and retain uncertain data.
3. Run focused non-destructive checks, then complete backend/UI/audit/format/OpenAPI checks for the integrated revision.
4. Inspect real synthetic runtime screenshots where UI changes affect understanding or safety.
5. Obtain a permitted independent review of the actual changed boundary. Do not retry or bypass a blocked review operation.
6. Repair findings and repeat. Record exact SHAs, test scope, skipped platforms and remaining gates.
7. Only consider wider acceptance after unresolved high-consequence findings are closed by evidence. Customer/device validation and commercial/legal distribution holds remain separate decisions.

Every checkpoint should identify the next bounded experiment and the evidence needed, not invent a finish line from green CI. Automatic recovery removal remains disabled until SAFE-03 is independently satisfied.
