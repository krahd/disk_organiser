# Declared keep-current review

7 October 2026 · Pure-data planner correctness checkpoint

## Reproduced gap

Selecting Harbour's existing `working` volume and `Projects/Harbour` folder previously described all three unchanged members as copies, reported occupied self-collisions and required 76,005,000 bytes including reserve. That result did not implement the documented comparison with keeping the current placement.

Eighteen new synthetic tests reproduced 28 failing assertions against accepted source `8ecab6e04e3d1efb52771611b1e43b8cf9e03f06`, without import/runtime errors. The original 82 pure-data tests passed before the change.

## Disposition contract

The existing synthetic input and review versions remain unchanged. Each `proposed_changes` entry retains its source volume/address/version, intended volume/address and `source_retained: true`. Its `proposal` is now one of:

- `copy_with_project_structure`: the exact declared volume/address differs. Existing copy semantics and checks remain.
- `keep_current`: source and intended volume IDs and byte-for-byte relative address are identical, and the source identity prerequisites below are satisfied. This is a declared no-op, not a copy or operation.
- `unresolved_current_location`: the exact declared address matches, but an identity prerequisite is missing or contradictory. A `current_location_identity_unproven` blocker names the member. No copy or successful no-op is established.

Keep-current requires an online, completely observed source volume with known case and Unicode semantics; fresh volume and member observations against the fixture clock; a plain file with exactly one declared link and a non-null content version; and no declared source ancestor/descendant conflict. Source and destination share the same volume record because their exact IDs match. A label, failure-domain label, matching content version elsewhere, case-folded alias or canonically equivalent Unicode spelling is insufficient. The planner does not open or resolve any path.

This proof is only internal to the declared synthetic contract. It does not authenticate a live volume, object, version or current filesystem state. A fresh assertion remains an assertion.

## Collision and evidence scope

Only a proven kept member's own occupied-address check is skipped. Occupancy by any other member, planned overlap between kept and copied members, source ancestor conflicts and ordinary portable-name checks remain active. A case-only or Unicode-spelling change remains a proposed copy with the existing normalised collision checks; it is not silently treated as an alias or rename.

Keeping a member does not clear unreviewed membership, missing dependencies, unknown dependency completeness, changed/unknown declared relative layouts, backup requirements or failed/insufficient restore evidence. A review can therefore contain only kept entries, need no additional copy space, and still have protection or dependency blockers. `reviewable_proposal_only` retains its existing meaning: no synthetic rule blocker, never execution permission.

## Capacity contract

- `known_logical_copy_bytes` sums known sizes only for proposed copies. Kept and unresolved entries are not labelled or counted as copies.
- Unknown sizes of copies or unresolved entries remain listed in `unknown_size_member_ids`. An unknown size on an otherwise proven kept member is irrelevant to additional copy space.
- Any unresolved current-location identity or unknown required member size makes `required_destination_bytes` null. A zero known-copy subtotal is not a complete capacity result.
- A mixed plan counts only actual proposed copies and applies the policy reserve once. Even a zero-byte copy still needs the reserve.
- Only an entirely proven kept scope has zero applied `reserve_bytes` and zero `required_destination_bytes`. It requires no free-space assertion, so null observed free capacity remains visible without creating a copy-capacity blocker. The input policy reserve is not changed.
- `reclaimed_bytes` stays zero for every result because sources are retained. `physical_allocation_prediction` stays null. No physical allocation, current free-space or safe-to-erase claim is added.

## UI and regression boundary

The isolated UI now labels kept and unresolved entries explicitly and explains their capacity scope. Its HTML, CSS, controls, revision/race handling and routes are unchanged. Ordinary copy-only display text and both packaged reference outputs remain unchanged.

The prior HTTP/browser assertion that the exact current home must self-collide intentionally changes: the reference fixture now has three `keep_current` entries, no self-collision and zero additional required space. This is the behaviour being fixed, not a test weakened to pass. New negative HTTP/browser assertions target a different folder below the existing `edit.project` file and still require an occupied-path blocker. Planner tests additionally cover unselected occupied targets, kept/copied overlap, source ancestry, case/Unicode aliases, unsupported kinds, stale/future observations, missing version/link/name evidence, mixed/unknown/zero-byte capacity and unchanged protection/authority boundaries.

## Verification

Local candidate checks:

- 100 pure-data tests pass: all 82 original tests unchanged plus 18 keep-current tests.
- 22 isolated HTTP tests pass: the intentional same-home replacement plus two additional negative/uncertain cases; exact packaged-reference equality remains green.
- 122 frontend Jest tests pass: all 119 original tests unchanged plus three conditional-rendering tests.
- Full frontend formatting and Python compilation pass. All seven isolated Chromium scenarios parse/list successfully.
- A fresh local Chromium attempt reached the browser-launch step, but the locked Chromium executable is absent. No browser installation/download, alternate browser or security bypass was attempted. No local browser pass or pixel acceptance is claimed.

Independent review accepts the bounded pure-data source and tested HTTP/Jest behaviour: all 12 changed files and 49 unchanged supplied files match the accepted base/candidate manifest; fresh 100 planner, 22 HTTP and 122 Jest tests pass; a separate 3,356-case adversarial matrix passes; and both packaged outputs exactly match the baseline. It independently reproduces the 28 baseline assertion failures with no errors. Exact-source remote CI and inspection of the new keep-current screenshot remain required before rendered interaction acceptance. Older dependency-layout and interaction runs do not test this candidate. No real drive, provider, account, credential, application reference, backup/restore operation or historical mutation reproducer was used.

## Remaining limits

Authenticated layout and restore evidence, native observations, application-specific dependencies, execution/recovery, persistent projects and commercial readiness remain separately gated. All execution, undo, live-verification and source-erasure flags remain false/null. Automatic recovery deletion stays unavailable. Main integration and the documentation-publication trigger are coordinated separately. This candidate does not change a publication workflow or authorise deployment.
