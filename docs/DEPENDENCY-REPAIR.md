# Dependency repair evidence

This change does not perform blanket unverified production upgrades.

- Existing CI run [37274404313](https://github.com/krahd/disk_organiser/actions/runs/37274404313), job 111648148072, stopped at `pip-audit`: Click 8.3.2, Pillow 12.2.0 and pypdf 6.10.2 had known advisories. Their listed fixed minimums across that report were Click 8.3.3, Pillow 12.3.0 and pypdf 6.19.0.
- A fresh local `pip-audit` also identified Werkzeug 3.1.8 / CVE-2026-102598, fixed by 3.1.9. These four pinned packages were updated; the unpinned requirements carry matching minimum versions. Other production dependencies remain unchanged.
- Initial `npm audit` reported 39 vulnerable packages, including high-severity Jest transitive chains. Compatible `npm audit fix` updates were applied first. Remaining chains required explicit Jest and jest-environment-jsdom 30.5.2 updates. Both are development-only. The complete existing UI unit suite is rerun after changing the test runtime.
- The remaining development-only `sprintf-js` advisory (GHSA-hp3w-g68c-fv3c) is reached through `@istanbuljs/load-nyc-config` → js-yaml 3 → argparse 1. A narrow js-yaml override is used for that one consumer. Its actual call site uses `load`, retained by the replacement; a YAML configuration compatibility test covers the override. No audit finding is suppressed or globally ignored.

Final audit/CI results and exact revision belong in `docs/IMPLEMENTATION-CHECKPOINT.md`. Registry installs are from PyPI/npm; no credentials or external inference were used. Dependency health is point-in-time evidence, not a permanent security guarantee.
