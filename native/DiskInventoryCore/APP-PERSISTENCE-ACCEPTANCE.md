# Ordinary app-library persistence: owned validation

10 October 2026. This development-preview tranche adds a lazy native Save/Open route to the ordinary executable. All storage execution described here uses fresh owned parent capabilities. The default Application Support resolver is unexecuted in CI. This is not default-path user-device, signed-container, distribution or real-drive acceptance.

## Exact source

- Source: `86d3620bc34fb8b242a73af669a160863654e2e2`.
- Tree: `6b58ab2300ff953575bfaab30588c4731014595f`.
- PR merge checkout: `9bf5d05d4d1149ee1642849e81282564cf8549ad`, independently read back to the same tree. This is a distinct commit.
- Main baseline: `26f6e67194af2ec10bac31b6594ac89a79bc8380`.
- The 32 changed/new paths and 309 unaffected baseline blobs/modes reconcile to the remote tree. Integrated source-manifest SHA-256: `9dfe4b7325dec75117924c7f391d79a67d239f9ad00160b5418d92ed90bec328`.

The initial source `4a11d4f2` compiled the ordinary preview and separate probe but failed XCTest compilation on a private helper called from another extension file. Its tests, process flows, new pixels and downstream six-case gates did not run. The successor changes that test-only helper to internal without changing its assertions or any runtime, asset, workflow or probe byte. Earlier source review had also corrected ACL presence-bit handling, native Close-only lease proof and bounded truthful failure reaping.

## Actual native and other checks

Both [native push 38046725515](https://github.com/krahd/disk_organiser/actions/runs/38046725515) and [native PR 38046727680](https://github.com/krahd/disk_organiser/actions/runs/38046727680) compile the ordinary preview and the separately built owned-capability process probe, then pass:

- **194 unique XCTest methods**, zero failures; all 153 previous main method identities remain, with 41 additional methods.
- Six independently constructed native/Python fixture comparisons and six native snapshot/parser catalogue roundtrips. Both downstream steps actually ran.
- Eight bundled assets, two examples, 22 codec admissions, 4,102 encoding samples and 18 data-protocol cases.
- Ordinary empty-window process readiness and normal Quit, exit 0. Empty startup does not access the default storage resolver.
- A separate process-probe chain verifies one live lease blocks another process, normal close permits a fresh process to reopen exact saved fixture bytes, and forced exit of an owned child releases its lease. An unrelated owned descriptor is absent in the child. Failure cleanup has a separate bounded observed-reap test; it is not normal-exit evidence.

The runner records Xcode 16.4 build 16F6, SDK 15.5, Swift 6.1.2, arm64 macOS 15.7.9 build 24G830 and image `macos15 20260907.0337.1`. APFS refuses a test-owned invalid-UTF-8 filename with errno 92. Synthetic invalid-name rejection passes; native invalid-name acceptance is not established.

All 12 source push/PR workflows are green. The [aggregate push run](https://github.com/krahd/disk_organiser/actions/runs/38046725526) reports Linux 709 backend, 665 Jest and 27 browser journeys (the workflow uses `--grep-invert "preview modal"`, excluding that group) plus 44 routes. Windows reports **607 passed, 102 skipped**, plus 44 routes. Skips are not coverage; the quiet Windows log does not enumerate their identities or reasons. Local 11 persistence DOM, 16 ingress and 39 catalogue DOM checks are separate source evidence.

## Storage and interaction boundaries exercised

- Native Save/Open are discoverable, with the development/sample-only scope visible. Real-folder selection remains disabled.
- The fixed application-data factory resolves lazily. Missing Open creates nothing. Save uses one fixed setup namespace, canonical ownership metadata, no-follow descriptors, private file/directory metadata checks and a retained advisory lock.
- Unmarked, malformed, partial, symlinked, hard-linked, wrong-mode or replaced objects are preserved and refused. Complete empty setup can resume an explicit Save; no permission repair, migration or automatic cleanup occurs.
- Actual owned-descriptor absent-ACL admission and invalid-descriptor refusal pass. In-memory Darwin filesec/ACL tests prove present-empty admission, nonempty refusal and non-one presence semantics. They do not modify filesystem ACLs or claim real on-disk present-empty/nonempty coverage.
- Bootstrap state is separate from an uncertain Save result. The flight is reserved before suspension; Save captures edits after admission. Pre-Save cancellation keeps current work and may retain setup metadata. Late returned storage is retired, while an issued uncertain Save retains same-attempt Check.
- Open fences before admission. Missing/in-use/cancelled admission preserves the current catalogue, draft, selection and focus; the next explicit action can retry when applicable.
- Actual native Close releases the first window's lease before a second window opens the saved library. The acceptance path does not directly close the storage actor to manufacture this result.
- The native chooser validates and previews two historical locations before explicit replacement. Cancel preserves the current view; replacement discloses selection/search/comparison loss and never overwrites saved versions.
- Native AppKit/WebKit actions keep genuine pointer/keyboard events, readiness, hit and focus guards. Both logs contain 78 true native hit/visible-centre pairs. Full first-row bounds remain `(1, 3, 185, 32)` within the actual visible document; positive dimensions, flipped top origin and maximum 16-point top gap pass.

The ordinary application has no path argument/environment override. Only the separate test executable receives the freshly owned parent descriptor and bounded command pipes; no storage lease is inherited. The probe is not a Package product or ordinary application command interface. The foreign test descriptor is itself close-on-exec, so its observed absence is not uniquely attributable to the spawn-default flag rather than both protections together. Advisory locking does not claim protection against every same-user hostile writer. OS flush does not establish device power-loss durability.

## Original pixels and retention

The author opened all **26 unchanged original PNGs** at original detail. All original lengths and SHA-256 values match their generated manifests; five archive digests and sizes match GitHub. No fill, composite, crop, resize or replacement pixels were used for review.

The new ordinary-persistence views are 90–96: enabled controls, missing library, in-use refusal, cancelled preparation, saved state, native reopen preview and reopened WebKit header/count. The retained views are 60–64, 70–75 and 80–87.

Visual scope remains precise:
- Native chrome and sheet content are named-view regions, not full-window screenshots.
- View 95 is a 650×510 chooser content capture with full first-row geometry; its complete record preview remains scrollable.
- View 96 is a 1024×493 initial WebKit viewport showing two records in the count. Offscreen location cards are not claimed visible in that image.
- View 87 is deliberately scrolled; narrow views 63/64 show recorded history and uncertainty.
- The author found no captured text clipping or control overlap. This is development-preview acceptance; stacked developer notices are not a polished commercial UX claim.

Root evidence review personally inspected originals 90, 92, 95 and 96 and found their controls, recovery text, preview and reopened count legible. That is a four-view evidence review, not another hardware run or an all-view claim.

Original push artifacts are listed below. They are available through the linked native push run while GitHub retains them. Retention is 14 days; a hash record does not create a permanent image archive. The separate archive hold is unchanged.


| Artifact | ID | ZIP bytes | ZIP SHA-256 |
| --- | --- | ---: | --- |
| owned-application-library-screens | 11668125958 | 314686 | `f25ea56240ab2db4c125e27b802e4c51cba09e69ced35dbc1c5e7f37ab5a2821` |
| owned-native-application-screens | 11668450554 | 202075 | `702e7f4684be07d885fc0634e76df9a4f1e50481a7a23cd8c295371c1ef0dca1` |
| owned-native-library-interaction-screens | 11668275758 | 386114 | `07339fb9f4cc25d9f8bd8fd83f3ffba4cb626afc027b049d1042fb06fa722b3e` |
| owned-native-preview-screens | 11667836270 | 436351 | `63b058472063182f2b4e48e916d38a9895007499a6fce5127b51deb1d22b1b3b` |
| owned-native-inventory-goldens | 11667786442 | 2517 | `d15ee6b0d25e99337355a35a0866ca72370bdbf82aa043e6aa264d3959fb8fd6` |

Evidence-manifest SHA-256: `deb7aec3cfa51a09a488f85f215cd1ed51273bacc67056c350e19e0bdcfffac0`.

### New original identities

| Original | Dimensions | SHA-256 |
| --- | --- | --- |
| 90-application-storage-controls.png | 984×133 | `9156f243d3443a515b212f68136f38447b6ac7232aaa24f1ed7b2318203120b0` |
| 91-application-missing-library.png | 984×133 | `c020569b4dc3f0df25a79365b26a52a3e1de2cf791c019610bbc614ea92d847d` |
| 92-application-library-in-use.png | 984×133 | `a0468d27943a26b27a86d45596ad6b3538e1176ec5416b64b8ddb0f54793b2bb` |
| 93-application-preparation-cancelled.png | 984×133 | `31e6038164fecf9d4090cef222e63708fbb59495fb2e5b06e540563c80e96b49` |
| 94-application-library-saved.png | 984×133 | `4dd1921366635b35f8cc69249b6b20fe9a551cb8fd22c09763e0e0bc3d435577` |
| 95-application-reopen-preview.png | 650×510 | `df5eabdc69204a2ef6b7f81c92b751ec5b29cb1a349167adecdb7c9a36a565dc` |
| 96-application-reopened-records.png | 1024×493 | `e0ac3f38dbb189c5637daa5fb1f64d1290c262dcb51bbfad558c94ebfee40326` |

## Independent closeout and remaining gates

Independent closeout accepts this exact owned-fixture development slice. It verifies all 32 source paths, all 309 unaffected baseline blobs, both 194-method logs with all 153 prior identities, both downstream six-case gates, all 78 strict hit pairs per run, all five archives and all 26 unchanged original PNGs. Every original was personally opened. No source, executed-native or captured-pixel blocker was found. This is evidence review, not another hardware execution or broader product acceptance. Review SHA-256: `b9785f1d0dc79c3faf16f99d8493ab0e0b6223bc788c206b1e9de748883da0ec`; receipt SHA-256: `88afd79535f489d0be17f44ccbaaa85ae5f7380b9e0dcd0739cbf1fa97cc72be`. The source/pixel limits above remain unchanged. Dark appearance, high-scale accessibility and physical-device acceptance are not inferred.

All results above belong to the named source and tree. Final documentation-head workflows, guarded normal integration and actual-main checks remain separate gates. No actual default-path save/relaunch, signed container, permissions, folder grant, bookmark, drive identity, contents, capacity, backup verification, move/delete/restore or provider operation is accepted. Saved snapshots remain historical claims; persistence does not authenticate them.
