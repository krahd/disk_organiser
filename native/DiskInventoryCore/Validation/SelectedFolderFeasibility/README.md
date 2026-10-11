# Owned-folder feasibility: reconstructed contract checkpoint

This is a small, inert source checkpoint for a future read-only selected-folder
experiment. It is outside SwiftPM and workflows. It supplies no app, picker,
filesystem reader, signature observer, signing step or executable host.

The earlier unpublished 21-file host candidate became unavailable after the
local workspace changed. Its exact bytes and review artefacts could not be
recovered. These files are newly reconstructed and require their own review;
they are not the earlier candidate and inherit none of its test claims. Accepted
repository history through main `57078cd3` remains intact.

## Implemented now

`Tools/probe_contract.py` validates only bounded, caller-supplied JSON bytes or
in-memory inventory rows. Its immutable results are **claims**, not observed
files, authenticated seals, physical-drive identities or access grants. No
filesystem operation, path resolution, process, network or permission API is
called. Imported JSON cannot activate the existing observer or real-folder
button. The module's command entry refuses with exit 2 and reads no arguments.

- Fixture claims require an exact version/field set, canonical UUIDs, a
  case-bound bundle identifier, five fixed derived paths, four distinct claimed
  objects on one claimed filesystem/owner, owner-only fixture modes and the two
  fixed nonempty 32-byte controls. The example contains synthetic identifiers
  and a placeholder address which is never opened.
- Inventory claims require one directory root row, exact unique relative paths,
  complete real-directory parents, kind/mode agreement and bounded file sizes.
  Root metadata is validated; only descendants enter the descendant result.
- Links resolve against the complete supplied inventory, component by component.
  Each encountered link expands before any following parent component. Missing
  or regular-file intermediates, root escape, cycles and exhausted budgets
  refuse. No `normpath`, `realpath` or filesystem target lookup is used.
- JSON is checked for byte and nesting limits before parsing. Duplicate keys,
  invalid UTF-8, non-finite numbers, Boolean-as-integer and unknown fields refuse.
  Paths preserve exact Unicode spelling; size/path agreement is no content or
  backup proof.

Limits: 4 KiB fixture JSON, 8 MiB inventory JSON, 16 JSON nesting levels, 20,000
inventory rows, 1 KiB exact path/target text, 512 MiB per file and 2 GiB total
claimed bytes. Link resolution allows at most 40 expansions, 4,096 steps per
link, 200,000 aggregate steps, 1,024 pending components/16 KiB pending bytes and
128 resolved components/1 KiB resolved bytes, including the initial parent.
These are experiment limits, not product capacity or whole-drive coverage.

## Local source-only verification

From this directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s Tools -p 'test_*.py' -v
```

The reconstructed checkpoint has **32 passing memory-only methods**, including
a 19-case portable inventory corpus. The only test-file reads load the two
repository-owned JSON examples. No temporary disk probe, ACL, OS panel, native
application or user folder is created or accessed. A first author test exposed
an assumed Python recursion limit; the explicit 16-level parser guard and a
positive/negative boundary regression now pass.

The corpus includes both previously identified symlink-pivot escapes, valid
nested and parent-relative links, file/missing/cyclic intermediates, root and
absolute escapes, trailing-slash refusal, a 40/41 expansion boundary and input
budgets. Accepted cases assert exact resolved destinations as well as descendant
sets; refusals assert their exact reason. Paired below/above pending-budget cases
resolve ultimately to a directory, so a regular-file guard cannot mask the
budget oracle. Python consumes it here; a future Swift consumer and differential
negative-parser corpus remain unimplemented. These results cannot be counted as
native or prior-candidate coverage.

## Retained defect lessons and missing work

1. Root rows and descendants must use the same representation. This checkpoint
   implements that pure contract; actual produced/observed inventory comparison
   still needs the future controller.
2. Freeze and verification must bind the **complete** approved raw test
   configuration and resolved paths/environment, not just the method name.
   Configuration sealing and signature inspection are not implemented here.
3. Future reads must acquire nonblocking, no-follow regular descriptors and
   admit type, identity and size before bounded reads/enumeration. This module
   admits only already-supplied bytes; it is not a safe file-reading API.
4. Each acquired descriptor must be registered immediately, transferred
   explicitly and retired once. Ambiguous close must refuse, attempt the other
   owned retirements and never retry the ambiguous integer. No descriptor
   lifecycle exists in this checkpoint.
5. Future control bytes must be read through the identity/ACL-checked descriptor;
   any separate write-open must match the same object. Claimed metadata here
   supplies no causal OS-access evidence.
6. Link expansion must precede parent traversal. The pure inventory resolver and
   corpus implement this, including an explicit initial-depth bound. They do
   not prove anything about a real filesystem or sandbox.

## Next gates

Reconstruct and independently review only the next small missing source slice,
then save it reversibly before expanding further. The later host needs a native
signature/ACL observer, bounded descriptor controller, exact SDK/runner review,
complete immutable build-to-run configuration, AppKit/UI source and native
compilation. Existing product source admission and the real-folder control stay
closed. There is no new workflow or host dependency.

Build/ad-hoc signing and genuine sandbox-panel selection are separate runtime
authority gates. They would use only fresh owned GitHub-runner fixtures, exact
reviewed products and the two proposed host entitlements: App Sandbox and
user-selected read-only files. Unknown runner permissions, profiles or extra
entitlements must stop the experiment. No user-device/default-path execution,
persistent bookmark, security setting, filesystem ACL change or release is
included. General repository-save permission does not supply these runtime
permissions. Original native pixels and independent execution acceptance are
still required before any real-folder capability claim.
