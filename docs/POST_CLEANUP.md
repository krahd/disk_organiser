Repository sanitization & forced history rewrite
=================================================

Date: 2026-04-24 UTC

Summary
-------
- Archived noisy/diagnostic workflows to `.github/archived-workflows/` and removed their active copies from `.github/workflows/` to stop accidental push-triggered empty runs.
- Added `.gitignore` entries to ignore release zips and common build outputs.
- Removed tracked `release-v0.1.1.zip` from HEAD, purged it from git history, garbage-collected, and force-pushed rewritten refs and tags to `origin`.

Why this matters
-----------------
Rewriting history was necessary to remove a tracked binary artifact. Because refs and tags were rewritten and force-pushed, local clones and forks will have diverged history and must be updated carefully to avoid data loss.

What changed (key items)
------------------------
- Active workflows deleted: `.github/workflows/tag-debug-importlib.yml`, `.github/workflows/debug-bottle-build.yml`, `.github/workflows/ci-action-test.yml`
- Archived copies: `.github/archived-workflows/tag-debug-importlib.yml`, `.github/archived-workflows/debug-bottle-build.yml`, `.github/archived-workflows/ci-action-test.yml`
- New/updated: `.gitignore` now contains rules that ignore `release-*.zip`, `dist/`, `out/`, and common virtualenv dirs.
- Removed file from HEAD and history: `release-v0.1.1.zip` (purged from all branches and tags, force-pushed on 2026-04-24).

Immediate actions for collaborators
----------------------------------
If you have no uncommitted local changes and you do not have unpushed local branches you care about, the simplest, safest approach is to re-clone:

1) Re-clone (recommended):

   git clone https://github.com/krahd/disk_organiser.git
   cd disk_organiser

2) If you prefer to keep your existing clone, follow these steps (careful — these commands will discard local commits if you reset without backing them up):

  # Optional: make a local backup of all refs
  git bundle create ~/disk_organiser_backup.bundle --all

  # Reset your local main branch to the new remote main
  git fetch origin
  git checkout main
  git reset --hard origin/main

  # For other local branches that track remote branches, reset each one to the remote counterpart
  git checkout feature/your-branch
  git reset --hard origin/feature/your-branch

If you have local commits that are not pushed anywhere, create patches first (`git format-patch`) or create a branch (or bundle) to preserve them before resetting.

Tags and branches
-----------------
Tags and branches were rewritten and force-pushed. If you rely on historic tags, please re-fetch and reset as above. Some tag names were re-created during the purge.

Notes & follow-ups
------------------
- The archived workflow copies are kept under `.github/archived-workflows/` for reference and can be restored later if needed.
- If you want me to help rebase any local branches with unpushed commits onto the rewritten history, tell me which branches and I will generate a safe sequence of commands or perform the rebase for you.

Contact
-------
If anything looks wrong after you update your local clone, send me the output of `git status --short` and `git log --oneline -n 10` and I will advise next steps.
