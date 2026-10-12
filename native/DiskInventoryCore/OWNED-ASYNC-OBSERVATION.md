# Responsive owned observation (source checkpoint)

The internal ObservationJob runs one already-admitted core controller on a
serial worker. It has no path, URL, bookmark, JSON authority or source factory.
The ordinary app still depends only on DiskInventoryDesktop and uses bundled
examples. DiskInventoryCore and the closed selection adapter remain unlinked
from that product; no user-folder control is activated.

## Ownership and cancellation

The existing synchronous observer remains the only metadata walker. Its
source admission, no-follow and filesystem boundaries, race guards, exclusions,
2,000-entry/500-per-directory/depth-eight limits and cooperative five-second
budget are unchanged. An asynchronous job invokes it once. The test-only
provider still prepares its own small fixtures and admitted lease using the
existing constructor; only the active observation moves off the main actor.
This is not a claim that every fixture-setup operation is background I/O.
Worker-invoked test release, I/O and controller-seam callbacks are formed
explicitly as Sendable closures with locked captures. UI callbacks remain
main-actor isolated. This follows [Swift SE-0306 closure isolation](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0306-actors.md#closures);
no actor runtime check or established synchronous seam API is weakened.

Cancel sets a lock-protected request. The worker consumes it through the core's
existing cooperative cancellation callback, so descriptor retirement stays
with the observing worker. It does not close a borrowed descriptor or pretend
to interrupt a blocking syscall. A pre-start request is consumed when the job
runs; an unstarted job retains its controller until run or deinitialisation.
This differs deliberately from calling core.cancel on another thread before
start, where release could still be in progress when a failed observation
returns. One job owns one continuation; repeated run refuses before installing a caller's cancellation handler, so a rejected cancelled caller cannot cancel the first.

After observe returns and takeSnapshot performs one-use admission, the job
makes one locked terminal decision. A cancellation request before that decision
discards any bytes, including bytes already taken from the core. Later
cancellation cannot rewrite the delivered immutable result. The separate
LibrarySession generation fence still discards success or progress from a
cancelled/replaced preparation before WebKit staging. Lease retirement precedes
all terminal delivery; cancelled, failed and unavailable outcomes have no
admitted snapshot.

## Progress and UI

Progress is an inspected-entry count, never a completion percentage or content
read/backup claim. A single latest-value slot coalesces counts; values must be
monotonic and in 0...2,000. Cancel and terminal completion clear the slot. There
is no callback task per entry. The test-only provider owns one main-actor
20ms delivery task, cancels and joins it before returning, and passes only the
bounded count value. Production bundled examples do not invent progress.

LibrarySession updates the existing native status only while the matching
generation is preparing. Stopping/closed/newer generations ignore late values.
The active native Cancel button keeps its genuine event/hit-test path. Saving
remains subject to the existing session/interaction fence; progress cannot
stage a snapshot or write a saved catalogue.

## Authored verification, not executed acceptance

The repaired source retains all 217 baseline XCTest identities and adds sixteen,
for 233 authored methods. Thirteen new job tests cover success/worker affinity,
pre-start and active cancellation, descriptor retirement, cancellation between
core admission and job publication, late cancellation after success, rejected
cancelled second-run isolation, coalesced bounds, Task cancellation/weak lifetime,
partial symlink gaps and failure. Enumeration and projection/admission cancellation
use the job entry point and verify every owned descriptor retires. Success and
failure also have weak job-lifetime and exact ownership checks. Three session tests cover bounded values, stale progress across a
cancel/retry and Close reentry from active progress.

The existing native selection journey is strengthened to hold once at the first three-entry
progress callback of a real owned observation, show the count in original capture73,
perform an actual AppKit Cancel, prove no added record, then retry and add.
The first draft incorrectly targeted an unreported count and is retained with
the changes-requested source receipt; the walker itself is unchanged.
Its unchanged capture helper still checks real geometry, original dimensions
and alpha, without fills or composites. The existing application-data journey
now saves two real owned observations, verifies their temporary source folders
are gone, reopens through the native saved-library controls and types a search
through native keys. It asserts each exact path/size/record pairing, the retained partial-record
badge, trusted keydown/keyup targets, the resulting query and zero new source
calls, and captures the actual reopened search region as96. This is an offline
saved-record test, not a physical unplug or user-volume identity test.

A separate held-success test provider obtains and retires real owned bytes
before withholding their delivery. It positively returns those bytes after
Cancel/Close, preserving the session pre-stage fence rather than substituting
a worker cancellation error. Retry preparation is also exercised.

Core callback admission closes before the final root guard. A late job request
still suppresses terminal bytes, but may not prevent that guard or projection
from running. No interruptible-syscall or hard cancellation deadline is claimed.

Only the five pure Python isolation-rule tests have run locally for this
checkpoint. The actual graph command cannot run here because xcrun is absent;
no Swift compile or native method has executed for these changed bytes. Frozen
independent source review, hosted macOS compilation and all233+6+6 gates,
existing browser/asset gates, exact original-pixel review and final-main
verification are still required. CI wiring and limits are unchanged. Prior
native counts and screenshots belong to their earlier exact sources.
