# Project organisation and protection review prototype

This is a pure-data, synthetic-only planning demonstration. It is part of Disk Organiser's wider drive/project administration direction. It cannot scan, back up, restore, move, copy or delete real files.

From this directory:

```sh
python -m unittest discover -v
python demo.py
```

`project-review-example.json` is a reviewable synthetic case. `project-review-blocked.json` demonstrates uncertainty and protection gaps. Use `planning_preview.loads` for the strict JSON boundary, then `planning_preview.review`. The `revise` function demonstrates a user-corrected membership/destination with stale-revision protection.

The example's “verified” records are fictional test inputs. Every output keeps live backup/restore verification false, execution authority null, and undo/source-erasure permission false. No existing Disk Organiser execution module is imported.

Selected dependency IDs alone do not establish layout fidelity. Changed declared parent-relative dependency addresses require review; cross-volume or unknown naming semantics remain unknown. See [the bounded dependency-layout check](../../docs/drive-administration/DEPENDENCY-LAYOUT.md). This check does not validate application references or approve relocation.

The exact current home can produce explicit `keep_current` entries when declared identity prerequisites hold. Uncertain current locations remain unresolved with unknown required capacity. Mixed plans count only proposed copies. See [the keep-current contract and verification boundary](../../docs/drive-administration/KEEP-CURRENT.md).

The cost module is an explicitly incomplete illustration with dated public prices, clear unit assumptions and omitted costs. It is not a quote.

See [the slice contract](../../docs/drive-administration/NEXT-SLICE.md), [product roadmap](../../docs/DRIVE-ADMINISTRATION-ROADMAP.md), [provider research](../../docs/drive-administration/PROVIDER-ECONOMICS.md) and [verification limits](../../docs/drive-administration/VERIFICATION.md).
