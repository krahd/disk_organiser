# Disk Organiser v0.1.1 (2026-04-18)

## Highlights

- Preview modal UX improvements: grouping, collapsible groups, and clearer actions.
- Merged Safe-mode visual CI changes and resolved merge conflicts.
- Added dry-run and preview support for undo operations and recycle cleanup in `backend/op_store.py`.
- Scan index rebuild now supports `dry_run` and respects RQ/Redis usage when available.
- Repository cleanup: removed compiled Python artifacts and updated `.gitignore`.
- Applied Prettier formatting to frontend and added dev scripts in `package.json`.

## Screenshots

<!-- Attached assets -->

- Screenshot: https://github.com/krahd/disk_organiser/releases/download/v0.1.1/screenshot-1.svg
- Screenshot: https://github.com/krahd/disk_organiser/releases/download/v0.1.1/screenshot-2.svg

You can embed these directly in Markdown with `![screenshot](URL)` if desired.

## Full changes

- chore: format frontend with Prettier (commit 9013593)
- Merge PR #2: resolved conflicts and merge into main (commit 20d279a)
- Resolve merge conflicts for PR #2: merge origin/main into pr-2, merge package.json, remove pyc artifacts (commit 268fea2)
- chore: ignore compiled Python files (*.pyc) (commit bbce097)
- Merge feature/safe-mode-visual-ci into main (commit 41c9a57)
- feat(preview): modal UX, grouping, collapse, and tests (commit 7d8ad09)
- Fix lint issues, run formatters, update lint config (commit 14e2a7c)

## How to run

Backend:

```bash
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
python backend/app.py
```

Frontend (dev):

```bash
cd frontend
npm install
# run tests
npm test
# format
npm run format
# open `frontend/index.html` in a browser or serve with a static server
```

## Notes

Assets attached to this release:

- `release-v0.1.1.zip`
- `screenshot-1.svg`
- `screenshot-2.svg`

Please report issues at https://github.com/krahd/disk_organiser/issues.

