# Guided-copy implementation checkpoint

## Scope and ancestry

- Repository: `krahd/disk_organiser`; main observed at `c01668510b3b8e8e899390d1e3a0c1a74ad79db3`.
- Preserve existing safety branch `ai/workspace/disk-organiser-fs-safety-20261005-c7`, head `c7b39fb3ea1fb3b53f709ab63eb0b7d7c883a991`, as parent of the new dedicated branch `codex/safe-guided-organisation-20261006`.
- Copy-first POSIX workflow only; no mutation of real user data during implementation. All fixtures are synthetic temporary files. See `GUIDED-COPIES.md` for product and recovery limits.
- Draft review checkpoint, not full-product/commercial acceptance. MIT rights, commercial wrapper and distribution holds are unchanged. No Apple uploads, merge, release or deployment.

## Verification so far

- Local full pinned-environment backend suite: 116 tests passed. Focused flake8 on the guided engine and new Python test files passed.
- Local UI unit tests: 4 suites, 23 tests pass, including preview/approval/repeated-click handling, filename escaping and interrupted-request messaging.
- OpenAPI route coverage: 44 routes passed. Full frontend Prettier check passed.
- Python audit: `pip-audit -r backend/requirements-locked.txt` found no known vulnerabilities after four targeted fixes.
- Node audit: zero vulnerabilities after tested development-tool updates and a narrow js-yaml 4.3.2 override. YAML consumer compatibility passed.
- Real runtime UI/screenshot suite: executed on ordinary GitHub CI with synthetic fixtures; see the exact-revision evidence below. The restricted local browser environment was not bypassed.

## Resume and independent review

1. Verify the dedicated remote branch and draft PR head before changes.
2. Check CI for that exact SHA. Require Linux backend, Windows legacy/backend suite, dependency audits, formatting, UI unit tests and real Flask/Playwright synthetic flow. Windows guided tests skip intentionally.
3. Review the synthetic-browser-evidence artifact: desktop/mobile exact preview and persisted recovery. No source-user files may be added to fixtures.
4. Request an independent safety review of stale/race boundaries, interrupted journal states, copy ownership, original-preserving recovery and UI approvals. Implement findings on the same dedicated branch and rerun affected checks.
5. Remaining product work: native Windows guided operations, macOS filesystem/device acceptance, broader metadata/cloud/network handling, bounded async scan/cancel UX, and separately audited move/delete semantics. Do not claim a release or complete all-product acceptance from this checkpoint.

## Remote checkpoint and CI repair

- Draft PR: https://github.com/krahd/disk_organiser/pull/11
- Initial implementation SHA: `2000c2cba31c0ceb81eb5fcbff17796472bdd974`, remotely read back.
- Initial PR CI run `37497015208` passed the Python dependency audit, then exposed a collection error in the preserved pre-existing safety test because Linux changed into `backend/` before importing the `backend` package. Both OS jobs now invoke `python -m pytest -q backend/tests` from the repository root, matching local verification. This preserves the regression test rather than deleting it.
- Repaired implementation SHA `7a4ab232e79f34818e3e7a5534f2aaedaa47f434`: [PR CI 37497309003](https://github.com/krahd/disk_organiser/actions/runs/37497309003) and [push CI 37497302056](https://github.com/krahd/disk_organiser/actions/runs/37497302056) both passed.
- At that revision: Linux 115 backend tests passed; Windows 96 passed / 19 explicitly unsupported guided tests skipped; 23 UI unit tests passed; both dependency audits, formatting, OpenAPI and all 4 browser tests passed.
- [Synthetic screenshot artifact](https://github.com/krahd/disk_organiser/actions/runs/37497309003/artifacts/11428097333), SHA-256 `ddbdbff454f59a7dc9ab921430af12a583e999bfc375a1c292db368628ed1ce9`, was downloaded and its desktop preview, mobile preview and recovered-state images were visually inspected. Artifact retention is 14 days.
- Screenshot review led to a final focused refinement: mobile action cards instead of horizontal table scrolling, non-zero byte display for small files, and reviewable copy paths before recovery. All UI pages also deny framing, including the retained legacy interface. Local regression coverage is now 116 backend tests and 23 UI tests.
- The final refinement's exact-head CI is checked after publication and recorded in the PR conversation. Do not attribute the predecessor's green result to later code without that check.
