# Inactive fixed host direct-dependency inspection

## Baseline and purpose

[PR59](https://github.com/krahd/disk_organiser/pull/59) merged the target-only Debug
layout correction at main `1c9f7c08433c3ebe0185f32fb81814ef7bbbb808`, tree
`f70d0f309bcf61d2a230f3ce6bcbfae0c248dd0d`. Source
`3cd46909e5f558ef997760dec6380fed043904cc` and PR checkout
`1044adccb16f2fc725caecd60e272c6a18568ca7` have that same tree. All twelve source/PR
and six actual-main ordinary workflows passed on attempt one. Every native lane
retained 233 distinct methods plus six differential and six parser cases, 82 true
hit/visible-centre pairs and four Cancel phases; every browser lane passed thirteen
journeys. Earlier ordinary UI delivery flakiness remains unresolved. No new pixel
review or experimental corrected-layout build is claimed.

- Main [native job](https://github.com/krahd/disk_organiser/actions/runs/38466033660/job/115532944107):
  220,399 original bytes, SHA256 `4fe1826f0305c6be9182a7b82ff4afa057f786bde027fd01e69acadf7655b470`.
- Main [browser job](https://github.com/krahd/disk_organiser/actions/runs/38466033551/job/115532943645):
  60,426 original bytes, SHA256 `ff97ebd39f4f55a8f2f3964101407d736de74606375af495275908083833e08e`.

[Consumed run ten](RUN-TEN-ACTIVATION.md#terminal-result-and-deactivation-2026-10-13)
remains historical unsigned-build success followed by host signing failure.
The one-setting repair's actual layout and signatures are still unmeasured.
This successor requires explicit direct-dependency evidence and the expected
one-executable host layout before a later build-only result can be accepted.

## Fixed inspector and trust boundary

One static command is added after the three unchanged explicit signing commands:

`/Applications/Xcode_16.4.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/otool-classic -arch all -L <owned Products>/Debug/OwnedFolderProbe.app/Contents/MacOS/OwnedFolderProbe`

Its target comes only from the retained owned workspace relationship. It is data
passed to the inspector; it is never launched. There is no PATH/xcrun fallback,
recursive discovery, caller-supplied binary, new signing target or blanket deep
signing. Existing signatures and exact entitlement requirements are unchanged.

The fixed inspector leaf is checked before build and immediately before/after
inspection: a regular executable, root-owned, not group/other writable, nonempty
and at most 64 MiB. Device, inode, mode, uid, gid, size, nanosecond modification
and change times must match. Missing or changed identity refuses. This is a
trusted-runner/toolchain check, not a cryptographic signature or authentication
of every ancestor. It does not eliminate malicious replacement races. The exact
leaf's presence/type and actual output on this runner remain unmeasured.

Apple's [cctools project](https://github.com/apple-oss-distributions/cctools/blob/e0d56624eca2a76c2ace4c21850df9e666de4ca5/cctools.xcodeproj/project.pbxproj)
and public-tool configuration define the classic product and selected-toolchain
usr/bin installation. That primary source plus the measured Xcode Developer
prefix supports this proposed path. It is not an inspected SDK binary manifest.
All nine primary URL/byte/hash receipts are in [STATIC-DEPENDENCIES-SOURCES.json](STATIC-DEPENDENCIES-SOURCES.json).
No Apple source is built or copied into the implementation.

## Strict acceptance and remaining limits

Exactly one arm64 and one x86_64 section must name the complete owned executable.
Every line must be a complete formatter record. Each slice has 1–64 unique
canonical absolute dependency names, including exact `/usr/lib/libSystem.B.dylib`.
Only `/usr/lib/` and `/System/Library/Frameworks/` descendants are admitted, with
bounded ASCII components and no empty/dot/parent components. Per-architecture
sets may differ. Names ending `.debug.dylib` and `__preview.dylib` are refused,
as are relative, @rpath/@loader_path/@executable_path, private and third-party
paths. Unexpected diagnostics, qualifiers, duplicate sections/records or missing
slices refuse. Versions use bounded unsigned 16.8.8 components and only the
primary formatter's weak/reexport/upward/lazy qualifiers or no qualifier.

The [primary formatter](https://github.com/apple-oss-distributions/cctools/blob/e0d56624eca2a76c2ace4c21850df9e666de4ca5/otool/ofile_print.c)
and [Apple's own qualifier test](https://github.com/apple-oss-distributions/cctools/blob/e0d56624eca2a76c2ace4c21850df9e666de4ca5/tests/test-cases/otool-classic-L/Makefile)
anchor the grammar. The checked-in text fixture is labelled our synthetic
assembly of that grammar, not measured runner output. This cctools revision is
not claimed to be the exact runner binary's source.

The existing bounded descriptor-owned final inventory must contain exactly its
host MacOS directory and one nonempty regular OwnedFolderProbe executable there.
An extra debug/preview library, other leaf, directory or link refuses even after
successful signing and dependency parsing. No separate broad traversal is added.
The result establishes an accepted direct install-name set and expected owned
layout only. It does not prove transitive closure, system-library existence or
signatures, dyld resolution, loadability or app/sandbox behaviour. A legitimate
SDK/Swift @rpath dependency may conservatively refuse; retain its actual output
for separate review rather than widening policy automatically.

## Budgets, evidence and source validation

The fixed command ceiling increases from 31 to 32 by this single slot. All
original command bodies/order, signing arguments and individual ceilings remain.
The new slot has a twenty-second ceiling and 65,536 combined-output-byte bound;
stderr must be empty. Stdout is strict ASCII, newline terminated, at most 130
nonempty lines of at most 1,024 bytes and dependency names at most 512 bytes.
The 720-second work, 180-second finalisation, nine-second retirement allowance,
existing total evidence bounds and twenty-minute workflow ceiling are unchanged.
Raw output/arguments/retirement facts remain in the existing trace/packet. Any
preflight, process, parser, identity or layout failure stops admission without
retry, preserves first failure and independently retires owned capabilities.

All 438 local memory/mock methods pass, retaining all 420 prior identities and
adding eighteen. Nineteen structural checks and six default refusals pass;
233 ordinary native method sources stay exact. Tests cover the source-derived
fixture, both architecture orders, each malformed record/path/version family,
64/65 records, 512/513-character paths, exactly 65,536/65,537 bytes, each tool
identity field, every command argument/order/repeat and deadline boundary,
eleven full-controller early failure models and three final-layout refusals.
All tool/filesystem operations in these tests are mocked. Initial author runs
found stale historical template literals and a test-only formatting assumption;
the corrected final tests retain the historical hashes and strict assertions.
No actual tool preflight, binary read, compile, sign, host/UI execution or new
operational run occurred. Independent final source review and successor ordinary
CI are still pending at this checkpoint.

## Inactive composition and later gate

False, consumed ten, the same ref, both experimental workflows absent and seven
historical markers remain. Nineteen host rows still bind the reviewed host-only
object `33c3e70daa2a3f89896e8d2141e01aff577592bb`. Four helper bodies change;
ten other operational helpers, sixteen historical inert anchors and standalone
diagnostic bytes remain exact. A new hash-only inert anchor binds current pins.
The exact PR59 inactive profile is retained in debug-layout.profile.inert so
its historical copy oracle is not rewritten as evidence for this inspector.

No next counter is selected and ten cannot be reused. Later activation requires
independent source acceptance, ordinary source/PR/actual-main checks, a separately
frozen immutable counter/ref and complete stable-identity history, then the exact
final trigger gate. No app/UI/panel/grant/user-drive or Stage C authority follows
from this source change. Ambient encoding-marker influence and artifact-retention
limits remain explicit; this does not create a permanent build/image archive.
