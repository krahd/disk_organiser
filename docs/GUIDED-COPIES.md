# Guided copies: bounded first version

The default application at `http://127.0.0.1:5000/ui/` groups copies of a selected folder's top-level files by extension. Originals are **never moved, deleted, renamed or edited**. This is organisation and verification, not disk cleanup. It consumes additional space, does not establish backup redundancy and never declares source media safe to erase.

## Use

1. Start with `python backend/app.py` after installing the pinned requirements. The Flask debugger is off unless explicitly enabled with `DISK_ORGANISER_DEBUG=1` for development.
2. Choose an absolute, fully local, unsynchronised folder on macOS/Linux. Close other programs that edit it. A folder picker is not implemented.
3. Scan to produce a saved preview. Review every source, destination, reason, byte count and skipped entry. No copies exist yet.
4. Tick the explicit approval/local-folder checkbox, then create the copies. SHA-256 hashes and original metadata are rechecked before applying the entire plan and for each copy. The plan expires after one hour.
5. Review the output under the unique `Organised-<plan-id-prefix>/` directory. Originals remain in place. Copy contents are verified, but original ACLs, extended attributes, resource forks, Finder tags, timestamps and permissions are not preserved; copies use private permissions.
6. History survives app restarts. To undo, separately approve recovery. It removes only generated inode-identified files with the expected full hash while the original remains unchanged, then removes only owned empty directories. Recovery never recreates missing originals or deletes added/edited files.

## Boundaries and honest failure states

- At most 500 directory entries and 1 GiB of supported source data per plan. No recursion. Unrecognised extensions, hidden entries, directories, symlinks, hard links, special files and unreadable entries are skipped with reasons.
- Only POSIX descriptor-relative APIs are supported. Windows guided operations fail closed; legacy Windows tests remain separate. Windows support is not implied by a green Windows job.
- Known synced paths, dataless/offline flags and cloud-provider attributes are rejected before file-content reads. There is no universal cloud/network detector. The explicit local-folder confirmation is required. Arbitrary provider placeholders, network filesystems, hostile concurrent writers and mount replacement are outside this first version's guarantee.
- A 16 MiB free-space reserve is required beyond the total copy size. Space can change during execution: a failed write stops further work, journals an interruption when possible, and leaves originals intact. Quotas/permissions are reported through actual failures, not inferred from a successful preflight.
- SQLite uses full synchronous journal writes. Intent and ownership are saved before copying. File and directory fsync calls provide the supported filesystem's durability guarantees, not an absolute guarantee against faulty storage or power loss.
- A process crash can leave an `applying` or `recovering` state. Refresh history and explicitly recover; never automatically reapply. A repeated successful apply returns the same completed result without creating another output tree.
- Incomplete files, unknown ownership during a crash gap, edited copies, changed/missing originals, replaced folders and user additions are retained with exact conflict paths for manual inspection. Recovery is deliberately bounded rather than a promise to reverse arbitrary later changes.
- The journal is not automatically pruned. The UI shows the latest 50 plans. Retain the local state directory while recovery is needed. Source/development state lives in `backend/`; set `DISK_ORGANISER_DATA_DIR` to a private local directory to relocate it.
- Guided UI uses no external fonts/scripts, model providers, credentials, telemetry or remote inference. All filesystem API endpoints, including legacy endpoints, now require a localhost Host and reject a different Origin. Guided POST additionally requires JSON and a process token. Separate-origin frontend/CORS deployment is no longer supported. Do not proxy/expose this application publicly.

## Legacy compatibility

The previous interface is retained at `/ui/index.html` for compatibility but is not linked from guided navigation. Its move/delete/AI paths do not inherit the guided copy transaction guarantees. Existing backups/history remain untouched. The dangerous permanent-delete fallback has been removed: missing trash support now raises an actionable error without deleting anything. The existing branch `ai/workspace/disk-organiser-fs-safety-20261005-c7` is preserved as the ancestry of this change, including canonical-root validation and execute-time revalidation.

## Verification and release gates

Synthetic tests cover complete and repeated apply, persisted recovery, source changes, destination/case collisions, symlinks, hard links, FIFOs, unreadable entries, cloud attributes, insufficient space, mid-copy ENOSPC, journal failure, interruption, edited copies, replaced directories, user additions and concurrent app operations. Playwright's real Flask workflow uses only freshly generated synthetic files and records desktop/mobile preview and recovery screenshots in CI. This is not representative-volume, adversarial multi-process or physical-device certification.

MIT rights are unchanged. The private commercial wrapper and all paid-distribution eligibility holds remain unchanged. No deployment, release or Apple upload is authorised by this implementation.
