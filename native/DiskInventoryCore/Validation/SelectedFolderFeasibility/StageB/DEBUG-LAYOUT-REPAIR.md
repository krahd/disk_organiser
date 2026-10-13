# Inactive host Debug layout correction

## Evidence and cleanup

The consumed [run-ten build](https://github.com/krahd/disk_organiser/actions/runs/38459886396)
completed unsigned universal arm64/x86_64 host and UI-test-bundle compilation.
Signing the test bundle and runner returned zero. Host signing failed with an
unsigned nested OwnedFolderProbe.debug.dylib. The [terminal record](RUN-TEN-ACTIVATION.md#terminal-result-and-deactivation-2026-10-13)
retains the original failure, all 26 packet members, seven retired children/groups
and cleanup limits. No experimental app, UI test, panel or drive access occurred.
The actual output also contains __preview.dylib; its signing behaviour was not
separately measured and is not labelled another observed failure.

[PR58](https://github.com/krahd/disk_organiser/pull/58) integrated deactivation at
main `f339177c7a9d56134d43bef0e3d9c0b9e109bd74`, tree
`e8076a7e065fbf815e6c2b4bb81e144c30ab9f03`. Source
`cbf7e95a339bb79e982a129ae5d5bc34299f77af` and PR checkout
`33efdbd311677ae941168f02d52ff4b7896da9cf` have that same tree.
All twelve source/PR and six actual-main ordinary workflows passed first attempt.
Each native lane retained 233 distinct methods plus six differential and six
parser cases, 82 true hit/visible-centre pairs and four Cancel phases. Each browser
lane passed thirteen journeys. Earlier ordinary UI delivery flakiness remains
unresolved; no new original-pixel review is claimed.

- Main [native job 115521212309](https://github.com/krahd/disk_organiser/actions/runs/38462564766/job/115521212309):
  220,343 original bytes, SHA256 `79897efb85d46c5f1327079ea653e7e17e217a174bdc6cc97f5a51b0757e2933`.
- Main [browser job 115521204315](https://github.com/krahd/disk_organiser/actions/runs/38462563214/job/115521204315):
  60,521 original bytes, SHA256 `df25c000b6c60b11e27f16004cb91961c29e1ceafe304167c1751b53e5463646`.

## Exact source change and provenance

Only the OwnedFolderProbe target's Debug build configuration gains
`ENABLE_DEBUG_DYLIB = NO`. Project-wide, Release and UI-test settings are unchanged.
All Swift source, optimisation/debug/test properties, architectures, entitlements,
sandbox/security settings and signing arguments stay exact. The AppKit probe has
no Previews use. No signing path is omitted or dynamically discovered.

The reviewed [host-only object](https://github.com/krahd/disk_organiser/commit/33c3e70daa2a3f89896e8d2141e01aff577592bb)
changes that one project file, parented by inactive main above. All nineteen host
rows were read back and compared byte-for-byte, including Git and SHA256 hashes.
No branch moved to the intermediate object; the final pin-chain commit retains
it as parent. Project SHA256 is
`0d4ff1da5512a714504b5d41ba9631548c0194523a557f518694e2e4f00c7f23`,
12,983 bytes. Host-row aggregate is
`c1d6b20ff69af014533c7b586790a7aafceff0e84670887a63db53c41779bf2c`.

Profile remains False, counter ten consumed and ref unchanged. All fourteen
operational helper bodies, eighteen other host inputs, fifteen older inert
anchors, historical profile copies and the standalone diagnostic remain exact.
Both active experimental workflows are absent and all seven consumed markers
remain intact. The new inert anchor changes only the full current profile pin.
The exact inactive predecessor profile is retained for the historical run-ten
copy oracle. The earlier hook-only row delta now compares its fixed historical
profile rows, while all current file/row/aggregate assertions still bind the
current source. No old run is relabelled as testing this new layout.

Three added source-only methods verify the exact setting/full-file reversal,
wrong-scope/value/security/optimisation/unrelated-byte refusals, and inactive
row/anchor composition. All 420 local memory/mock methods pass, retaining 417
previous identities. Nineteen structural checks and six default refusals pass;
233 ordinary native test sources remain unchanged. Final composition review and
ordinary successor CI are pending. No new Xcode compile or signing was run.

## Primary basis and explicit acceptance gap

Apple's [build-product layout guidance](https://developer.apple.com/documentation/xcode/understanding-build-product-layout-changes)
documents the debug/preview-library layout and this per-target opt-out. The
[build-setting reference](https://developer.apple.com/documentation/xcode/build-settings-reference)
describes the setting. Its expected effect is to link host code directly into
the executable instead of the separate debug library and disable Previews for
this target. Current primary sources were checked on 2026-10-13; this is a
source-supported prediction, not measured Xcode 16.4 output for the new setting.

Apple's [signing guide](https://developer.apple.com/library/archive/documentation/Security/Conceptual/CodeSigningGuide/Procedures/Procedures.html)
requires nested components to be signed before their container. The existing
fixed test-bundle, runner, host order and their exact signing arguments remain.
No blanket --deep signing, new signing target or fallback is introduced.

The current 31-command, 720-second work plus 180-second finalisation, twenty-minute
job envelope is unchanged and inactive. Later acceptance requires original build
output and bounded owned product inventory proving the expected layout, plus
static direct-dependency evidence for both arm64 and x86_64. Missing dylibs and a
valid host signature alone cannot establish absence of dangling dependencies.
A separately reviewed fixed static inspector proposal may add one command, but
is not included here and has not run. It will not establish full transitive
dependency closure or application runtime success. Counter ten cannot be reused;
no new counter, trigger, app/UI/picker/grant/user-drive or Stage C is authorised
by this source checkpoint. Existing ambient-marker and 14-day artifact-retention
limits remain; no permanent image or build archive is implied.


## Later inactive direct-dependency source

The separately reviewed plan is implemented in the inactive [fixed static
dependency inspector](STATIC-DEPENDENCIES.md). It adds one explicit command and
a strict one-executable inventory requirement without adding signing targets.
Actual corrected-layout compilation, tool availability/output and full signed
acceptance remain unmeasured; this historical checkpoint's 31-command claim
remains attached to its original source.
