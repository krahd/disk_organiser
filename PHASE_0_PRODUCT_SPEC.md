# Phase 0 — Product Spec & Acceptance Criteria

Goal
----
Define the product vision, user personas, high-priority user journeys, and clear
acceptance criteria so engineering can begin Phase 1 (API stabilization) with
unambiguous goals.

Scope (Phase 0)
- Draft product spec and success metrics.
- Define personas and primary user journeys.
- Produce MVP feature list and acceptance criteria.
- Create a sign-off checklist and a small backlog of initial issues.

Personas
- Primary: Home-user (non-technical)
  - Needs: recover disk space safely, easy-to-understand recommendations, undoable actions.
  - Key constraints: minimal UI complexity, default safety settings.
- Secondary: Power-user / sysadmin
  - Needs: fine-grained controls, scripting/CLI, ability to run on servers.
  - Key constraints: performance, batch operations, reproducibility.

Key User Journeys (MVP)
1. Discover duplicates and preview safe moves
   - As a Home-user, I want to scan a folder and get grouped duplicate files so I can understand potential cleanup actions.
   - Acceptance criteria:
     - POST /api/duplicates returns groups with `files[]` including `path`, `size`, and `hash` where applicable.
     - Frontend renders groups and allows user to request suggestions.
2. Create suggestions, preview and execute with undo
   - As a Home-user, I want to receive suggested moves, preview the moves as a dry-run, then execute with an undoable backup.
   - Acceptance criteria:
     - `POST /api/organise` (heuristic) and `POST /api/organise/suggest` (AI) return suggestions in the documented contract.
     - `POST /api/organise/preview` creates an operation object persisted to ops-store with an `id` and `backup_dir`.
     - `POST /api/organise/execute` with `dry_run=true` returns a preview `preview` and `summary` without writing to disk.
     - Executing without `dry_run` moves files to destinations and stores backups in `backend/ops_backups/<op-id>`; `undo` restores from backups.
3. Visualise disk usage
   - As a Power-user, I want to open a treemap or sunburst view to quickly find large directories and duplicates.
   - Acceptance criteria:
     - `POST /api/visualisation` returns a hierarchical structure suitable for treemap rendering.
     - Frontend lazy-loads D3 and renders interactive treemap with drill-down and tooltips.

MVP Feature Prioritization
- High: duplicate scanning, preview/execute/undo, visualiser basic treemap, safe backups.
- Medium: scan-index pruning and rebuild UI, background jobs (SSE for progress), OpenAPI.
- Low: fuzzy similarity for images/audio, cloud model connectors, telemetry (opt-in only).

Non-functional Requirements
- Privacy: no file content is sent to external services by default.
- Safety: destructive actions must be reversible via backups or rejected if backups fail.
- Cross-platform: support macOS, Windows, Linux path handling.
- Performance: scans should be resumable and allow user limits (max_files, min_size).

Deliverables (end of Phase 0)
- `docs/PROJECT_PLAN.md` (roadmap) — created.
- `docs/PHASE_0_PRODUCT_SPEC.md` — this file.
- A short issue list for Phase 1 and Phase 2 (to be created in the repo).
- Acceptance criteria checklist for the engineering team.

Proposed Timeline & Owners
- Duration: 1 week (draft + review + sign-off).
- Owner: Product lead (or repo owner). I can create the initial PR and issues if you want.

Sign-off Checklist
- [ ] Product spec reviewed and agreed by stakeholder.
- [ ] MVP feature list and acceptance criteria approved.
- [ ] Top 3 engineering risks identified and mitigation plan attached.
- [ ] Issues created for Phase 1 and Phase 2 with clear descriptions and acceptance criteria.

Next steps (I can take these)
- Create a PR with `docs/PROJECT_PLAN.md` and `docs/PHASE_0_PRODUCT_SPEC.md`.
- Open GitHub issues for Phase 1 (API spec) and Phase 2 (index hardening).
- Run a short UX spike to produce a treemap prototype (frontend branch).

Questions for you
- Who should be the sign-off owner (GitHub user/org) for Phase 0?
- Do you want me to create the PR and issues now, or save them as drafts for review?
