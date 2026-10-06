# Backup provider and commercial research

Checked 6 October 2026. Official public sources only. Public marketing and technical documentation do not establish an executed reseller contract, programme admission or a guaranteed margin. No accounts, credentials, purchases, communications or live backups were created.

## Recommendation

Start with a software fee and customer-owned storage. Evaluate a documented backup engine behind a narrow adapter, beginning with imported synthetic evidence. Add optional referrals after confirming programme eligibility. Consider branded storage only after measuring support, restores, retention and customer-exit costs.

The reseller opportunity is real, but storage margin alone is not a defensible business. The product earns its place through useful drive/project administration and reliable control of protection.

## Verified provider facts and their implications

### Backblaze Computer Backup

- The current [pricing page](https://www.backblaze.com/cloud-backup/pricing) advertises $99/year for Personal and Business backup. Business includes administrative features. This is an advertised price, not an obtained Disk Organiser wholesale quote.
- The [MSP guide](https://www.backblaze.com/partners/msp-guide-faq) states 10% lifetime Computer Backup commissions, a $100 payout threshold, no B2 commission, permission to set B2 customer pricing, and no Computer Backup white-labelling. The [current MSP page](https://www.backblaze.com/partners/roles/msp) instead directs prospective partners to enquire about margin. Treat the older guide as programme evidence to reconfirm, not an unconditional revenue commitment.
- [Supported-data documentation](https://www.backblaze.com/computer-backup/docs/supported-backup-data) excludes NAS/network-mounted storage and explains that Computer Backup is not an extra archival storage system. It is not the universal target for every disk-administration job.
- The specific [external-drive guidance](https://www.backblaze.com/computer-backup/docs/external-hard-drives) ties disconnected-drive retention to the selected history: default 30 days versus up to one year with extended history. The latter is not retroactive. Renamed drives need reselection. Avoid encoding a universal “reconnect every 30 days or lose it” rule without the customer's actual setting.

**Commercial use:** optional referral or managed-account integration when the customer's devices and retention fit. Do not silently represent it as Disk-branded software or durable offload storage.

### Backblaze B2 and embedded storage

- [B2 pricing](https://www.backblaze.com/cloud-storage/pricing) currently starts at $6.95 per billed TB per month. It includes egress up to three times average monthly stored data; excess is $0.01/GB. No minimum storage duration or minimum file-size fee is advertised. Class A/B/C calls are free for pay-as-you-go; Class D has separate pricing. Do not carry forward an older $6/TB assumption.
- [Powered by Backblaze](https://www.backblaze.com/cloud-storage/poweredbybackblaze) explicitly describes embedded storage, custom branding/billing and partner usage reporting. [API documentation](https://www.backblaze.com/apidocs) lists separate Native, S3-compatible and Partner APIs. This is a promising route for a future wrapped service; contractual eligibility, discounts, commitments and support terms remain unknown.
- [Region documentation](https://www.backblaze.com/docs/cloud-storage-data-regions) lists US West, US East, EU Central and Canada East. Region is chosen per account and cannot subsequently be changed within that account; migration involves another account. EU Central is Amsterdam. Record region at setup and account for migration overlap.

**Commercial use:** the strongest first technical candidate for bring-your-own object storage, subject to engine compatibility and security review. The embedded programme is a later commercial option, not a prerequisite for a useful first product.

### Wasabi

- [Pricing](https://wasabi.com/pricing) currently starts at $7.99/TB/month. [The pricing FAQ](https://wasabi.com/pricing/faq) sets a one-TB active-storage monthly minimum and a 90-day object-duration rule for pay-as-you-go. Early deletion produces a remaining-duration charge. Its free-egress guideline expects monthly downloads no greater than active storage; sustained excess can lead to limits or suspension. API fairness conditions and a 4 KB billable object minimum also matter. “No egress fee” is not unlimited unconstrained download entitlement.
- The [reseller programme](https://wasabi.com/partner/become-a-partner/resellers) describes channel support and consolidated service administration. [Account Control Manager](https://wasabi.com/cloud-object-storage/tools/account-control-manager) supports multi-tenant account/billing workflows and a custom-branded console. No fixed reseller discount or guaranteed commission is published on the inspected pages.
- [Storage regions](https://wasabi.com/company/storage-regions) include US and several European locations; bucket region is chosen explicitly. [Service URLs](https://docs.wasabi.com/docs/service-urls-for-wasabis-storage-regions) provide the authoritative endpoints. Never assume all EMEA regions are in the EU.

**Commercial use:** plausible later alternative for stable, larger retained archives and managed multi-account service. Small individual datasets, frequent pruning and repeated full restore/check downloads need careful economics and policy review.

## Packaging options

| Model | What Disk sells | Customer/provider relationship | Main risk | Recommended stage |
| --- | --- | --- | --- | --- |
| Software + bring your own storage | Administration, policies, coverage and supported engine control | Customer keeps storage contract and billing | Adapter maintenance and customer confusion about support boundaries | First |
| Referral/affiliate | Software plus an optional disclosed recommendation | Customer contracts with provider | Low revenue; attribution/eligibility; biased recommendations | Additional revenue after eligibility check |
| Reseller/MSP | Software/service and provider capacity/backup licence | Disk may manage accounts or billing | Payment exposure, support, access rights and customer exit | After operational evidence |
| Embedded/white-label | Disk-branded storage/backup service | Contractual architecture depends on provider programme | Full product expectations; security; margins; retention and liability | Later, with explicit agreement |

Wrapping an object store still requires a backup engine, encryption/key design, version/retention control, restore workflows, local scheduling, support and billing. A provider's storage durability does not prove the customer's backup completeness or application recovery.

## Integration order and boundaries

1. **Synthetic target and evidence records:** the delivered prototype. No integrations or credentials.
2. **Imported evidence from a known local backup format:** validate producer/version, exact scope, time and exclusions. Treat imported assertions as reports unless independently corroborated.
3. **Read-only supported engine adapter:** inspect declared snapshots/manifests through a version-pinned, allowlisted interface. Even a command described as a check may create locks or caches, so establish the actual side effects before using it. Never connect an arbitrary command string from plan JSON to a subprocess.
4. **Local backup/restore control:** explicit task scopes, new empty restore destinations, cost/capacity preview and independently reviewed operations.
5. **Customer-owned B2/S3 target:** selected region, secure locally stored scoped credentials, client-side encryption policy, network/retention/cost limits, restore tests and account-exit instructions.
6. **Another provider, then resale:** qualify customer demand and per-provider differences rather than assuming S3 compatibility means identical lifecycle, object-lock, billing or restore behaviour.

Restic is a candidate because its [documentation](https://restic.readthedocs.io/en/stable/045_working_with_repos.html) exposes snapshots, manifests, JSON output and repository checking. A structural check is not a full data read; full reads cost bandwidth. Its [restore documentation](https://restic.readthedocs.io/en/stable/050_restore.html) describes overwrite and deletion options that a wrapper must constrain. No restic executable was installed or run for this task; distribution/licence/version and platform acceptance remain future checks.

Rclone's [check command](https://rclone.org/commands/rclone_check/) compares source/destination size and supported hashes, with a download-based option. This can be useful integrity evidence, but is not versioned-backup policy or a complete restore exercise. Do not substitute a successful object listing, timestamp, sync or ETag for verified recovery.

Proprietary client status integrations, including Arq, CCC, Time Machine and Computer Backup, need a documented supported interface or explicit cooperation. Product marketing does not establish a stable integration API. Do not scrape private application databases as the default commercial contract.

## Unit economics to measure

Use the following accounting structure rather than a single advertised per-TB number:

`monthly contribution = software/service receipts + storage receipts + realised referral income − provider charges − payment/merchant fees − refunds/chargebacks − support time cost − operating costs − risk reserve`

Provider charges include active storage, retained versions, immutable retention, early-deletion liability, minimum account charges, request charges and transfer/restore/check costs. Carry the provider's actual billing unit, region, currency, effective date and contract in every estimate. Show tax separately until the seller's actual treatment is established. Do not equate decimal TB with binary TiB.

Illustrative sensitivities, not customer offers:

- A hypothetical $79/year software subscription yields about $6.58/month gross recurring equivalent before costs.
- The older 10% Computer Backup commission applied to the current $99 annual price is $9.90/year per licence. It should not finance unbounded support.
- At a hypothetical $11.99 per B2-billed-TB monthly resale charge and $6.95 storage cost, the difference is $5.04 before requests, excess egress, support, fees, taxes and risk. One 15-minute support incident costed at $30/hour is $7.50.
- For Wasabi, a 100 GB individual account may still incur the one-TB minimum. Deleting data early does not immediately eliminate the associated storage liability. High-churn policies must account for that before recommending the provider.
- Full backup checks, sample restores, emergency restores and migration downloads share transfer budgets. B2's free allowance depends on average storage, while Wasabi's fair-use guideline depends on active volume. A migration that reduces stored data can change the economics at precisely the moment downloads increase.

The included `prototypes/drive_administration/cost_preview.py` computes explicitly limited B2/Wasabi storage/transfer illustrations from fabricated byte amounts. It does not produce a quote, tax amount, negotiated margin or complete total cost. Wasabi's [billing-unit article](https://docs.wasabi.com/docs/does-wasabi-use-base-2-or-base-10-in-billing-calculations) explicitly confirms binary units. The B2 calculation uses decimal TB/GB as a clearly labelled modelling assumption; the exact byte-unit contract was not independently established from the inspected pricing page and must be confirmed before a quote.

## Contract and operating questions before managed resale

- Eligible seller entity/countries, programme admission, signed resale/branding rights, fixed/variable margin, quotas and minimum commitments
- Which party owns each account, bucket, encryption key and customer relationship; whether exit or account transfer is possible
- Billing frequency, currency, taxes, failed payments, refunds, suspension timing, data-retention grace and restore access during disputes
- Level-one support responsibility, escalation, incident communication, restore assistance, service commitments and liability allocation
- US/EU data location versus billing/support metadata, subprocessors, encryption/key custody and applicable DPA/transfer terms
- API entitlements, limits, account isolation, audit access, credentials rotation and breach response
- Data portability, supported independent restore, export cost, retention/object-lock constraints and termination handling

These are qualification requirements, not legal conclusions. Have suitable legal/security review before offering a managed backup contract. Relevant published documents include [Backblaze's DPA](https://www.backblaze.com/company/policy/dpa-for-eea-eu-residents) and the provider terms linked from the official pricing/programme pages. No terms have been accepted in this research.
