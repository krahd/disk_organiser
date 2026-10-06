# Guided copies: safety repair and current limits

## Current acceptance hold

The first copy-first candidate had a critical journal-trust flaw: persisted metadata could influence filesystem operations without complete validation. Its earlier green CI is **not safety acceptance**. Defensive repair is in progress and requires permitted independent confirmation before use beyond synthetic development fixtures.

Automatic recovery removal is disabled. Originals, generated copies, incomplete copies and journals are retained. A journal's inode/hash claims do not by themselves prove ownership. The application does not delete generated files during recovery, does not automatically migrate old journals, and never declares source media safe to erase.

## Read-only default and capabilities

The repaired app is read-only by default. `/api/guided/session` and `/api/guided/plans` expose a capability/uncertainty object: current mode, scan scope, whether experimental copy apply is enabled, recovery disabled, Disk Model not yet implemented, remote inference disabled, entry/byte bounds, and known uncertainty categories. The narrow file-type preview is not the intended intelligent Disk Model.

Synthetic development tests may explicitly set `DISK_ORGANISER_ENABLE_GUIDED_COPIES=1` when starting a single process. This exposes the restricted copy foundation only; it does not grant safety acceptance or enable removal. The following apply steps refer only to that opt-in fixture-testing mode. Default users can scan and inspect without Apply.

Legacy execute, undo and backup-removal APIs are also disabled by default; literal dry-run requests remain read-only. A separate `DISK_ORGANISER_ENABLE_LEGACY_MUTATIONS=1` flag exists only for preserving isolated compatibility tests, not as a recommendation to use legacy mutation paths.

## Current workflow

1. Start the single-process local application with `python backend/app.py` after installing pinned requirements. The debugger is off unless explicitly enabled with `DISK_ORGANISER_DEBUG=1` for development. Do not expose or proxy the service publicly.
2. Choose an absolute, fully local, unsynchronised folder on macOS/Linux. Close other programs editing it. A folder picker is not yet implemented.
3. Scan to produce an exact deterministic copy preview. The complete versioned schema is validated before persistence. Only this freshly generated in-process snapshot can authorise copying; its canonical digest is retained in memory, separate from the editable journal.
4. Review every source, destination, classification reason, byte count and skipped entry. No copy exists yet. Destination directory components are derived from the generated plan ID and a closed extension category mapping. Persisted paths must match those derivations exactly.
5. Explicitly approve copying and confirm that the folder is local and unsynchronised. Apply reloads and validates the complete journal, checks the exact in-process snapshot, verifies the root identity and all original snapshots, and checks space before creating anything. Copies use exclusive, no-follow creation. The in-process authorisation is consumed before applying.
6. Review the generated `Organised-<plan-id-prefix>/` folder. Originals are never moved, deleted, renamed or edited by guided mode. Copy bytes are verified, but source ACLs, extended attributes, resource forks, Finder tags, timestamps and permissions are not preserved. Generated copies use private permissions.
7. If work is interrupted, refresh history. Do not automatically resubmit, resume or remove files. Automatic recovery removal is unavailable. Keep originals, output and journal data while inspecting the reported state.

A process restart, one-hour expiry, snapshot alteration or eviction from the bounded in-process cache requires a new scan. Saved previews are historical data, not durable permission to apply. The in-process cache holds at most 128 previews. Multi-worker deployments are not supported by this authorisation model: a different worker will fail closed rather than infer permission.

## Persisted-data boundary

`backend/guided_schema.py` is a pure validator with no filesystem I/O. It rejects missing/extra fields, unsupported versions, duplicate JSON keys, malformed types, non-finite numbers, inconsistent byte totals, duplicate sources, unsupported categories, non-leaf file names, mismatched derived destinations, impossible state/result combinations, and ownership identities overlapping original sources or directories. Row ID and plan ID must match.

`backend/guided.py` validates on save, load, history and before apply. Apply additionally requires the trusted in-process snapshot; structural validity alone never grants file-operation authority. Invalid and older-version records are retained and counted as blocked history entries. Their untrusted paths are not opened, repaired or executed. No persistent signing key or credential is introduced by this repair.

The recovery endpoint validates the record then returns a safe-stop error. It performs no selected-folder I/O, unlink, rmdir, journal mutation or automatic cleanup. Re-enabling removal requires a separately designed and independently confirmed ownership/recovery mechanism.

## Supported bounds and unresolved cases

- Top-level supported regular files only; no recursion. At most 500 entries and 1 GiB of planned source data. Unknown extensions, hidden entries, directories, links, hard links, special files and unreadable entries do not become copy actions.
- POSIX descriptor-relative APIs only. Windows guided operations fail closed; green Windows legacy/backend tests do not establish guided Windows support.
- Known synced paths, dataless/offline flags and cloud-provider attributes are rejected before content reads. There is no universal cloud/network detector. Unknown cloud providers, network filesystems, hostile concurrent writers, mount replacement and storage faults remain outside acceptance.
- Copies consume extra disk space. This does not reclaim space, identify duplicates, provide independent backup redundancy or implement cross-volume media offload.
- A 16 MiB free-space reserve is required beyond copy size. Space/quota/permissions can change during execution: failures stop further work and retain originals. Partial or uncertain generated files remain for inspection.
- SQLite uses full synchronous journal writes; files and directories are fsynced. These mechanisms are not an absolute guarantee against faulty hardware or every filesystem's power-loss behaviour.
- Journal data is not automatically pruned. The UI shows the latest 50 records, including a count of blocked records in that window. Retain app state while inspection is needed. Source/development state lives in `backend/`; `DISK_ORGANISER_DATA_DIR` can select a private local state directory.
- The guided UI has no external fonts/scripts, model providers, telemetry or inference. All filesystem APIs require localhost Host values and reject different Origins. Guided POST additionally requires JSON and a process token. All UI pages disallow framing.

## Legacy compatibility and distribution

The earlier interface remains at `/ui/index.html`, outside default guided navigation. Legacy move/undo semantics have not received the guided schema/authorisation treatment and remain outside acceptance. Existing backups/history are untouched. Missing or failed trash support no longer falls back to permanent deletion; affected backup history is retained.

MIT rights and the private commercial wrapper's distribution holds are unchanged. No release, deployment, merge or Apple upload follows from this work. See `ARCHITECTURE-AND-OWNERSHIP.md`, `SAFETY-ACCEPTANCE-BACKLOG.md` and `IMPLEMENTATION-CHECKPOINT.md` for the current development boundary and verification evidence.
