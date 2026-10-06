# Disk Organiser: administer drives, projects and protection

Decision draft · 6 October 2026 · Product and implementation strategy

## Recommendation

Build a local-first administration product that helps a person decide where their work belongs, keep it organised across drives, maintain appropriate backup coverage, and recover it when needed. Sell the continuing reduction in storage-management effort. Offer storage and backup services as optional, separately costed extensions.

The initial customer journey should be **organise and protect a project across working, archive and backup storage**. The customer chooses the project and its intended home, corrects the proposed membership, sees what would change, resolves protection gaps, and eventually executes a separately safety-reviewed plan. The larger product expands this same model to all of a person's drives, projects and lifecycle policies.

A drive map, duplicate detector, file-type classifier or inventory can support this journey. None defines the product, its home screen or its commercial promise. The existing observation model can provide some inputs without requiring more work on its map UI. Product progress should be measured by completed administration jobs, not visualisation coverage.

This document is a proposed direction. The existing prototype is not sale-ready. The accompanying synthetic planning evaluator is a next implementation slice, not a complete organiser or functioning backup service.

## 1. What customers hire it to do

| Customer job | Useful outcome | Product behaviour |
| --- | --- | --- |
| Know where things belong | A comprehensible working/archive/reference layout across several volumes | Project and collection views; user-approved purposes; search across connected and historically observed offline drives |
| Consolidate a scattered project | Project and dependencies remain usable in an intended location | Explicit membership, dependency warnings, editable destination, preserve relative structure, app-specific relocation where necessary |
| Administer ongoing storage | New work follows clear rules without repeated sorting | Reviewed policies for inboxes, active projects, completed work, capacity reserves and archive review; observable exceptions |
| Know what is protected | The exact current project versions have suitable copies | Coverage by project and target, evidence freshness, exclusions, independent failure domains and unresolved items |
| Know recovery is practical | A bounded restore test succeeded and its limits are visible | Restore-to-new-location exercises, byte/metadata results, optional application-opening checks, measured time and cost |
| Control providers and costs | Appropriate targets, retention and spending without surprise | Bring-your-own storage, provider comparison, region and retention choices, budgets, usage, renewal/expiry warnings and export/exit routes |
| Replace or retire a drive | Data remains findable and protected after migration | A reviewed migration with capacity, integrity, coverage and application checks; source retirement is a distinct later decision |

### A coherent home screen

Show **Needs attention**, **Projects**, **Drives**, **Protection**, **Plans** and **Policies**. Lead with understandable work: “This project has changed since its last verified backup”, “Connect Archive B to finish this review”, or “Choose whether these exports belong with the project”.

An offline drive retains its catalogue with the last observation date. It never becomes an empty drive. A backup target is not treated as spare organising space. “No information” remains distinguishable from “nothing to do”.

## 2. Start with a customer who has a valuable problem

Recommended first research segment: independent creative professionals and very small creative businesses managing several external drives and project-based work. The segment is a hypothesis, not established demand. The attractive problem is the combination of scattered assets, project dependencies, active-versus-archive choices, offline media and uncertain backup coverage. The larger product remains useful for personal records, research, development and household storage.

The first paid proposition, after usability and safety gates, is:

> Keep your projects in the right place across your drives, with clear backup coverage and a practical recovery plan.

The first complete paid workflow must do useful administration, not simply deliver a scan report. A credible first release can cover one supported operating system, selected local volumes, a deliberately bounded project workflow, one supported local backup integration and one bring-your-own cloud target. It must say which project/application types it supports. Windows stays a first-class roadmap target but is not declared supported because a pure planner happens to run there.

### Validate value before commercial machinery

1. Show the synthetic journey and ask participants to organise a realistic project, correct a wrong grouping and explain the protection gaps.
2. Observe whether they can state what will change, what remains, which files are uncertain, the cost, and what recovery is actually available.
3. With appropriate permission and a qualified build, use non-critical representative data to establish real task completion and return usage.
4. Only after the intended paid workflow is useful, safe and distributable, test price and paid conversion. Do not take payment for functionality represented as complete while still only a fixture demonstration.

Suggested decision thresholds are explicit research criteria, not existing evidence: at least five representative users can finish the core review without developer intervention; no participant misreads a proposed plan as already executed or configuration as verified protection; repeat use reveals at least one meaningful ongoing administration job. Failing these criteria calls for simplifying the workflow or changing the initial segment rather than adding more integrations.

## 3. Commercial model and sequencing

### First: software fee plus customer-owned storage

The customer buys Disk Organiser for project/drive administration and protection management. Existing local drives and provider accounts remain theirs. This isolates the software's value, avoids financing stored data, and allows a simpler exit path.

Test a software-only annual price hypothesis around **US$79 per person**, with clearly defined device allowance and support, against a lower-priced perpetual organisation-only option if research shows maintenance value is too weak for a subscription. These are unpublished hypotheses, not approved pricing. Do not add an “unlimited backup” promise or bundle storage before measuring costs. The existing lower one-time launch hypotheses remain historical comparators, not active offers.

Recurring value should come from maintaining policies, reconnecting drive histories, detecting coverage regressions, checking retention, testing restoration and adapting plans. Safety warnings, recovery information and access to a user's own backups must never depend on an upgrade. Subscription expiry must not trap data or remove existing restore access.

### Second: optional referral revenue

Recommend a provider only when it fits the user's scope, region, retention and recovery needs. Make referral relationships clear. Treat affiliate income as incremental: using the older Backblaze guide's 10% and the currently advertised $99 annual Computer Backup price yields only $9.90 per annual licence before programme eligibility and other conditions. The current MSP page does not publish a binding margin; no commission entitlement is assumed. See [provider research](drive-administration/PROVIDER-ECONOMICS.md).

### Third: managed storage or branded backup add-on

Backblaze publicly describes an embedded/white-label B2 offering and Partner API; Wasabi offers reseller tooling and a custom-branded cloud console. These make a later wrapped service plausible. They do not provide Disk Organiser with an executed contract, discount, unlimited support, or a complete backup engine. [Backblaze embedded storage](https://www.backblaze.com/cloud-storage/poweredbybackblaze); [Wasabi account management](https://wasabi.com/cloud-object-storage/tools/account-control-manager).

Introduce this only after verifying commercial rights, customer ownership/exit, regional availability, account isolation, support responsibility, restore economics and billing. Charge a transparent software/service fee plus metered or bounded storage. Do not count provider list-price discount as the entire margin.

### Fourth: broader administration services

Potential later additions include guided drive migration, managed archive targets, hardware recommendations, recovery-support packages and small-team administration. Validate each against repeated customer jobs; do not turn an early consumer utility into an MSP platform by default. Support-assisted onboarding may be a separately scoped product once it can be delivered safely, but it is not a substitute for a usable product.

## 4. Competitive position

Existing products already cover important parts of the job:

- **NeoFinder** catalogues multi-volume media and backup archives, including offline library workflows and Backblaze B2. Cross-drive understanding and findability are not uncontested. [Official product](https://www.cdfinder.de/)
- **Hazel** automates folder organisation with user-created rules; its current single-user licence is $42. Rule-based organisation is not novel. [Product](https://www.noodlesoft.com/); [price](https://www.noodlesoft.com/kb/hazel-6-faq/)
- **Arq** offers software for customer-owned storage and a bundled backup subscription. Current advertised prices are $59.99 per computer for Arq 7 and $69.99/year for Premium with five computers and 1 TB. Backup packaging alone is already competitive. [Pricing](https://www.arqbackup.com/pricing/)
- **Carbon Copy Cloner** provides controlled local copying, snapshots, task history and several verification modes. Disk Organiser cannot differentiate by saying only that it checks backups. [Product](https://bombich.com/); [verification](https://support.bombich.com/hc/en-us/articles/20686511433623-How-to-verify-a-backup)

These are official advertised capabilities and asking prices, not hands-on reliability tests or market-share evidence. The proposed differentiation is an approachable decision-and-action layer joining **project intent, drive placement, dependency preservation, protection evidence and ongoing policies**. It must be demonstrated in a complete workflow. “AI” and “one dashboard” are insufficient differentiation.

## 5. The domain model

Keep these concepts separate:

1. **Volume:** stable app identity, available platform identifiers, filesystem semantics, observed mount, online/offline state, role, capacity evidence and last observation. A mount path or label is not persistent identity; cloned/reformatted media need reconciliation.
2. **Item/version:** observed address, content/version evidence, logical size, allocation uncertainty, link relationships, cloud-placeholder state, metadata requirements and observation freshness. Identical bytes do not imply identical purpose or permission to remove either copy.
3. **Project/collection:** proposed membership, user-confirmed membership, project-relative structure, dependencies, intended home, activity/lifecycle and confidence/source for each claim.
4. **Policy:** explicit scope, conditions, desired state, exceptions, safety prerequisites, budget and authorisation. A policy proposes before it acts until its operation class has separate automation acceptance.
5. **Target:** local volume, NAS, object storage or managed backup service; region, account ownership, capabilities, failure domains, billing and credentials reference. A sync service alone is not proof of versioned backup.
6. **Protection evidence:** configured scope; provider-reported job; snapshot manifest; byte verification; retention/immutability facts; and timestamped restore exercises. Evidence is scoped to item versions and exact targets.
7. **Plan:** immutable reviewed scope, exact effects, dependencies, conflicts, capacity/cost estimate, evidence references, user corrections and revision. It is a proposal until a separately trusted executor accepts fresh authorisation.
8. **Execution/recovery record:** actual effects and independently supported ownership/recovery evidence. It is not interchangeable with a proposed inverse in a JSON plan.

The current Disk Model may supply bounded observations and hypotheses. Extend it through an adapter when useful rather than treating its map or current schema as the product's permanent architecture. Its address IDs do not solve durable volume identity or rename tracking.

## 6. Important storage cases

- **External/offline drives:** preserve last-known state, request reconnection for fresh decisions, detect label reuse and volume changes. Never infer deletion from disconnection.
- **Cloud placeholders:** identify unknown/not-local content. Do not silently hydrate, upload or move it. A future approved hydration step must disclose download space, bandwidth and provider behaviour.
- **Symlinks/hard links:** model relationships and external references; do not follow or replace links as an implicit organisation shortcut. Multiple paths to one object do not create independent backups.
- **Application projects and libraries:** respect packages, media references, code repositories and app-managed databases. Preserve relative structure or use a supported native relocation/export workflow. Unknown dependencies stop the affected action.
- **Cross-filesystem moves:** account for case/Unicode collisions, metadata loss, permissions, timestamps, sparse files, clones, quotas and capacity during the entire operation. A copy on the same failure domain is not independent protection.
- **Backups and archives:** backup retention follows a policy; an archive is intentional long-term storage. A provider's live backup may age out deleted/disconnected source data. Keep the two user intentions explicit.
- **Versions and duplicates:** expose evidence and allow the user to declare authoritative copies and deliberate redundancy. Never convert similarity, age, filename or sampled content into disposability.

## 7. Protection evidence and restore claims

Use visible stages rather than one green “backed up” badge:

| Stage | What can be said | What remains unknown |
| --- | --- | --- |
| Configured | This policy is intended to cover these members | Whether any data reached the target |
| Provider-reported | A provider/client reports a job or snapshot | Exact included versions, exclusions, byte readability |
| Manifest observed | Exact members/versions appear in a known snapshot manifest | Whether all referenced data is retrievable |
| Content verified | The stated data was read and verified under a documented method | Whether a restore produces usable files/application state |
| Restore exercised | Specified members were restored and checked at a stated time | Untested members, later changes and other recovery scenarios |

Track incomplete coverage, mismatched versions, last-success and last-attempt separately. A successful sample restore proves its sample only. Byte checks and application-opening checks are different results. A changed file immediately makes earlier evidence historical for that new version.

Restic exposes snapshot/manifest inspection and distinguishes default structural checks from reading all backup data; a full data check can incur transfer cost. It is a candidate engine to evaluate, not an integration already implemented. [Repository checks](https://restic.readthedocs.io/en/stable/045_working_with_repos.html). Restoring should use an empty separately selected destination; existing-file overwrite and delete behaviour must never be inherited silently from an engine's defaults. [Restore semantics](https://restic.readthedocs.io/en/stable/050_restore.html).

## 8. Transaction, recovery and undo requirements

Existing mutation and automatic recovery-deletion holds remain intact. A future executor must satisfy an independent design and review before any real-drive acceptance:

1. Bind permission to an exact plan revision, authorised roots/volumes, typed operation and consequence summary. User edits, expiry, process restart or uncertain execution invalidate reusable authority.
2. Revalidate identities, freshness, paths, dependencies, destination names, permissions and capacity immediately before applying. Treat persisted/imported records as untrusted data.
3. Use a staged, bounded operation. For an initial copy-based relocation, retain originals; create destinations exclusively; verify content and required metadata; durably record known effects; stop when identity or outcome is uncertain.
4. Test interruption at each boundary and concurrent change. Never convert restart into automatic continuation or cleanup. Do not retry a write whose result is unknown without reconciling actual state through a separately trusted mechanism.
5. Design recovery around demonstrable ownership and known effects. An inode, hash, path or editable journal alone is insufficient. Record an honest retained/uncertain state when safe removal cannot be proven.
6. Design undo as a new checked operation with conflicts, preconditions and its own authorisation. If the destination or source has since changed, it must preserve new work and stop rather than overwrite. An inverse description does not establish undo support.
7. Source deletion, backup pruning, retention reduction and drive erasure remain separate consequential decisions. Copy verification is not a safe-to-erase certificate.

No broader filesystem acceptance is inferred from passing the pure-data tests shipped with this strategy.

## 9. Roadmap with exit gates

### A. Project administration review — next bounded slice

Implement the accompanying [slice specification](drive-administration/NEXT-SLICE.md): editable project membership and destination, preserved structure, conflicts and uncertainty, backup evidence by exact version, restore scope and capacity. Work only on synthetic records. Exit: deterministic contract tests; understandable review; no imports/calls into mutation code; no provider access; no executable action or undo claim. The local evaluator is implemented and tested as recorded in [verification](drive-administration/VERIFICATION.md).

### B. Real observations and a first useful review workflow

Add a permissioned native volume/folder adapter and project membership editor for one supported OS. Integrate bounded observation, offline-volume identity/history and a strict read-only backup-evidence adapter. First evaluate a standard, documented local backup engine/manifest format; avoid assuming every proprietary product has a stable public status API. Create exportable review records with private-by-default paths. Exit: representative non-critical data, explicit coverage, tested reconnect and stale-state handling, usability criteria met. No file execution is implied.

### C. Safe organisation and recovery

Deliver one independently qualified operation class: preserve a complete supported project in a new location while retaining originals. Require demonstrated dependency preservation, metadata fidelity, collision handling, capacity, interruption handling and recovery/undo limits. This is substantial engineering, not just turning an existing flag on. Exit: independent code and fixture review, required OS/filesystem tests, representative hardware acceptance and honest recovery UX. Broader moves and deletion are later operation classes.

### D. Protection management people can rely on

Add scheduled local backup control and one customer-owned object-storage integration through a supported engine. Show exact versions, exclusions, retention, freshness and bounded restore exercises. Credential storage and background access receive their own security review. Exit: end-to-end backup and restore tests, account/region/cost visibility, cancellation/retry behaviour, offline scenarios and no mistaken protection claims.

### E. Paid release and recurring administration

Package the supported complete journey with signing/notarisation where applicable, installation/update/uninstall tests, transparent terms, support, recovery access and export. Test software-only pricing only after the readiness gates. Add policy-driven maintenance gradually; automation permissions are per operation class and scope. Exit: paid conversions plus repeated useful administration, low support burden, no safety regression and measured contribution margin.

### F. Wrapped/resold services and broader platform

After measuring software retention and integration economics, qualify provider contracts and launch an opt-in managed storage add-on. Add other providers, multi-computer coordination, NAS support and small-team administration based on paid demand. Storage aggregation, multi-tenant administration, customer billing and support are their own product and security workstreams.

These are dependency gates, not promised calendar dates. Adding provider accounts or selling a storage plan is not an appropriate shortcut around the organisation and protection workflow.

## 10. Economics and operational gates

Measure software net revenue and contribution, not just gross storage resale. The cost ledger must include payment/merchant fees, taxes handled by the chosen seller arrangement, chargebacks/refunds, vendor storage, minimum retention, request/transfer costs, restore verification downloads, temporary restore capacity, support time, operating infrastructure and a risk reserve.

Storage support can overwhelm a small nominal markup. At an illustrative $11.99 monthly resale price versus a $6.95 provider cost, the $5.04 difference is before all other costs; one 15-minute support event valued at $30/hour costs $7.50. This is a sensitivity example, not a customer quote or earned margin.

For US/Europe, model the customer's selected data region, currency/tax handling, provider availability, billing unit and contract. “EU data region” is a placement setting, not by itself a complete privacy/compliance assurance. Require a legal/security review of the chosen customer/provider agreements, subprocessors, support access and international transfers before operating a managed service. The provider publishes a relevant [Backblaze DPA](https://www.backblaze.com/company/policy/dpa-for-eea-eu-residents); applicability to a future Disk service has not been determined.

Credentials belong in a platform secret store with least-privilege scopes. Keep secrets out of plan files, logs, analytics and support exports. Content and filenames remain local unless the user deliberately enables a named destination for a defined purpose. Provider billing identity, metadata and encryption-key custody need their own disclosure. Prefer customer-held encryption keys and a clear loss/recovery model; do not promise recovery when no party holds the key.

## 11. Measures that decide whether to continue

- Time to answer “where does this project belong and what is missing?”
- Corrected memberships/destinations and why the initial proposal was wrong
- Completed organisation jobs that remain usable in their applications
- Protection regressions detected and resolved; age of exact-version evidence
- Restore exercise success, actual duration, scope and cost
- Repeat administration usage, paid conversion and retention after real usefulness
- Support minutes per active customer, refunds, net software revenue and storage contribution
- Safety incidents, blocked uncertain operations, misleading-green-state reports and recovery conflicts

Do not treat scans, bytes visualised, nominal duplicate size or provider signups as sufficient product success. The long-term ambition is an everyday administration layer for personal storage. The next slice is valuable because it establishes the decisions and evidence that future action must honour.
