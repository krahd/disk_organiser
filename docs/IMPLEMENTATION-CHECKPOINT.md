# Guided-copy implementation checkpoint

## Scope and ancestry

- Repository: `krahd/disk_organiser`; main observed at `c01668510b3b8e8e899390d1e3a0c1a74ad79db3`.
- Preserve existing safety branch `ai/workspace/disk-organiser-fs-safety-20261005-c7`, head `c7b39fb3ea1fb3b53f709ab63eb0b7d7c883a991`, as parent of the new dedicated branch `codex/safe-guided-organisation-20261006`.
- Copy-first POSIX workflow only; no mutation of real user data during implementation. All fixtures are synthetic temporary files. See `GUIDED-COPIES.md` for product and recovery limits.
- Draft review checkpoint, not full-product/commercial acceptance. MIT rights, commercial wrapper and distribution holds are unchanged. No Apple uploads, merge, release or deployment.

## Verification so far

- Local full pinned-environment backend suite: 115 tests passed. Focused flake8 on the guided engine and new Python test files passed.
- Local UI unit tests: 4 suites, 23 tests pass, including preview/approval/repeated-click handling, filename escaping and interrupted-request messaging.
- OpenAPI route coverage: 44 routes passed. Full frontend Prettier check passed.
- Python audit: `pip-audit -r backend/requirements-locked.txt` found no known vulnerabilities after four targeted fixes.
- Node audit: zero vulnerabilities after tested development-tool updates and a narrow js-yaml 4.3.2 override. YAML consumer compatibility passed.
- Real runtime UI/screenshot suite: implemented for ordinary GitHub CI; not run in the restricted local browser environment.

## Resume and independent review

1. Verify the dedicated remote branch and draft PR head before changes.
2. Check CI for that exact SHA. Require Linux backend, Windows legacy/backend suite, dependency audits, formatting, UI unit tests and real Flask/Playwright synthetic flow. Windows guided tests skip intentionally.
3. Review the synthetic-browser-evidence artifact: desktop/mobile exact preview and persisted recovery. No source-user files may be added to fixtures.
4. Request an independent safety review of stale/race boundaries, interrupted journal states, copy ownership, original-preserving recovery and UI approvals. Implement findings on the same dedicated branch and rerun affected checks.
5. Remaining product work: native Windows guided operations, macOS filesystem/device acceptance, broader metadata/cloud/network handling, bounded async scan/cancel UX, and separately audited move/delete semantics. Do not claim a release or complete all-product acceptance from this checkpoint.
