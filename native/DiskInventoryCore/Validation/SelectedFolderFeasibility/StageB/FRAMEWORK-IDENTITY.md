# Disabled versioned framework-launcher candidate

The consumed create-event run [38315666563](https://github.com/krahd/disk_organiser/actions/runs/38315666563) refused before operational admission because Python reported the framework path rather than the pinned cache alias. It produced no build/signature/report evidence. The original reserved branch and both historical workflow anchors are retained. This source successor does not authorise another attempt.

## Exact path and observed facts

The disabled profile and third inactive anchor use only:

`/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12`

Both fixed `env -i` invocations retain `-I -S -B`, argument order and the existing startup/uploader environment allowlists. There is no path lookup, fallback, alias allowlist, installer, permission repair or generic resolver. The bootstrap still requires exact executable equality, version 3.12.10, all three isolation flags, Darwin and ARM64; CPython implementation is now explicit.

After the profile gate and before dispatch/source/owner admission, the bootstrap constructs a fresh seven-key `identity.interpreter` value. The report exports this as part of the existing 64 KiB `identity.json` envelope after operational work. The captured facts themselves require no filesystem/process operation. Early refusal still creates no report owner.

| Field | Exact shape and bound |
| --- | --- |
| `schema` | Integer `1` |
| `executable` | ASCII string, 1–256 bytes, no NUL; exactly the versioned path above and `profile.PYTHON` |
| `version` | Array of exactly three non-Boolean integers, each 0–65535; exactly `[3,12,10]` |
| `implementation` | ASCII string, 1–16 bytes, no NUL; exactly `cpython` |
| `flags` | Exactly `isolated`, `no_site`, `dont_write_bytecode`; each non-Boolean integer `1` |
| `platform` | ASCII string, 1–16 bytes, no NUL; exactly `darwin` |
| `machine` | ASCII string, 1–16 bytes, no NUL; exactly `arm64` |

The successful object is under 512 encoded bytes. Its shape comes from a fixed constructor, not user-provided JSON. No arbitrary environment, home, `sys.path` or source content is included. These are observed interpreter facts, not authentication of all loaded binary bytes.

## Why this candidate is evidence-based

The reported runner image tag resolves to `actions/runner-images` commit `9312c564c4df0b842ce00a6c202dccb519b8dfdd`. Its [toolset](https://github.com/actions/runner-images/blob/9312c564c4df0b842ce00a6c202dccb519b8dfdd/images/macos/toolsets/toolset-15.json) and [installer](https://github.com/actions/runner-images/blob/9312c564c4df0b842ce00a6c202dccb519b8dfdd/images/macos/scripts/build/Install-Toolset.ps1) select a Darwin ARM64 3.12 release from the Python versions catalogue. The matching 3.12.10 release source [package installer](https://github.com/actions/python-versions/blob/5ebefacc0b2900670e434765b8e0cdf41053cee7/installers/macos-pkg-setup-template.sh) links the cache's `bin` directory to the framework directory.

CPython 3.12.10's [Makefile](https://github.com/python/cpython/blob/0cc81280367df838c4b199f8f0378837165071c2/Makefile.pre.in#L1953-L2035) installs the versioned framework launcher and the unversioned alias. Its [macOS launcher](https://github.com/python/cpython/blob/0cc81280367df838c4b199f8f0378837165071c2/Mac/Tools/pythonw.c#L152-L211) resolves the containing directory while retaining the invoked basename; [getpath.py](https://github.com/python/cpython/blob/0cc81280367df838c4b199f8f0378837165071c2/Modules/getpath.py#L302-L320) uses that launcher value. This is consistent with the first run's observed spelling. The direct versioned path's future reported spelling is a source-based prediction, not a measured success. The expired runner's link metadata and downloaded package digest were not captured. The next attempt, if separately approved, must still refuse any mismatch.

## Remaining gates

The profile stays False, the active workflow is absent, and the third anchor is not runnable CI. Its provisional ref `validation/owned-build-framework-20261012` has not been created. The old marker `validation/owned-build-once-20261012` must not be changed, deleted or recreated. A fresh execution decision, exact activation review, green source/main checks and frozen payload cross-check are required before any new attempt. Case-variant refs can allocate a runner if the anchor is later activated; exact-case bootstrap admission still refuses them before operational owners.

All nineteen host inputs, the other thirteen operational module bodies, 31 command tuples, 720+180-second budgets and signature/retirement policies remain unchanged. Stage C, panels/grants and user-drive entry remain closed. Memory/mock tests establish source behaviour only; ordinary CI does not build or run this quarantined host.
