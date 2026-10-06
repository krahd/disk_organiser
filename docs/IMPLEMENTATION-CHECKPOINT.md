# Disk Organiser implementation checkpoint

Updated: 2026-10-06. Active state: safety repair and read-only product development. Independent acceptance is held.

## Current defensive core checkpoint

The candidate at `7ff5390a5401a674c77ccff743212b2297e1ca9d` is not accepted as safe: independent review found a persisted-journal authority flaw. Earlier passing CI and screenshots below are historical functional evidence only.

The current repair introduces a complete pure schema, derived leaf-only destinations, a fresh in-process preview authority check, read-only defaults and explicit capability/uncertainty reporting. Automatic recovery removal is disabled; originals, copies, partial outputs and journals are retained. Malformed/old journal records are never executed or silently migrated.

- Local pinned backend suite: 171 tests passed
- Guided engine/schema/test flake8: passed
- OpenAPI: 44 routes passed
- Source diff whitespace: passed
- Frontend safety-state integration: separately owned and pending
- Independent confirmation of the repaired boundary: pending

See [SAFETY-REPAIR-2026-10-06.md](SAFETY-REPAIR-2026-10-06.md) for exact changes, benign checks and residual gates. The repair does not reproduce the previously blocked review operation. A backend-only checkpoint may fail the old recovery-enabled browser expectation until the explicit UI integration lands; this must not be hidden or treated as a pass.

## Repository and integration

- Repository: `krahd/disk_organiser`
- Draft integration PR: https://github.com/krahd/disk_organiser/pull/11
- Dedicated branch: `codex/safe-guided-organisation-20261006`
- Main observed at `c01668510b3b8e8e899390d1e3a0c1a74ad79db3`
- Preserved prior safety ancestry: `c7b39fb3ea1fb3b53f709ab63eb0b7d7c883a991`
- Exact publication SHA and subsequent CI results are recorded in the PR conversation; verify the current head before any follow-on change.

[ARCHITECTURE-AND-OWNERSHIP.md](ARCHITECTURE-AND-OWNERSHIP.md) assigns disjoint core, UX, read-only model and reliability paths. [SAFETY-ACCEPTANCE-BACKLOG.md](SAFETY-ACCEPTANCE-BACKLOG.md) defines durable outcomes and acceptance gates. Do not overwrite another slice's files when integrating.

## Historical functional evidence, not safety acceptance

At `7ff5390a5401a674c77ccff743212b2297e1ca9d`, [PR CI 37498120176](https://github.com/krahd/disk_organiser/actions/runs/37498120176) and [push CI 37498113047](https://github.com/krahd/disk_organiser/actions/runs/37498113047) passed: Linux 116 backend tests, Windows 97 passed/19 skipped, 23 UI tests, four browser tests, audits, formatting and OpenAPI. The [synthetic screenshot artifact](https://github.com/krahd/disk_organiser/actions/runs/37498120176/artifacts/11428193219) had ZIP SHA-256 `a55677fbe14204c12f9237cc4ce9088dd7ad462ead9d690561c7bf1cc58a5d54`. Screenshots were inspected and drove mobile path/byte-display improvements.

Those checks missed the persisted-data flaw. They must not be reused as proof that the old recovery deletion is safe or that the new contract has been integrated.

## Resume sequence

1. Verify the latest PR head and apply only explicitly owned paths.
2. Integrate the capability-aware read-only UX and its revised real-runtime tests, retaining the complete backend regression suite.
3. Run exact-head backend, unit, dependency audit, formatting, OpenAPI and benign synthetic browser checks. Record supported/skipped platforms and inspect screenshots.
4. Obtain permitted independent confirmation of the schema/fresh-preview/no-removal boundary. Address findings before acceptance.
5. Continue the separate structured read-only Disk Model, explainable relationships, coherent read-only plans and long-run reliability work. Do not turn their output into direct filesystem or LLM operation authority.
6. Keep automatic recovery removal and ordinary mutation defaults disabled until their separate gates are met. Cross-volume offload, representative macOS acceptance, native Windows guided support and commercial distribution remain open.

MIT rights and commercial-wrapper holds are unchanged. No main merge, release, live deployment or Apple upload.
