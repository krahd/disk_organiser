# Disk Organiser — Project Plan & Roadmap

Date: 2026-04-18
Author: GitHub Copilot (working copy)

Overview
--------
This document captures the high-level plan and roadmap to evolve Disk Organiser
from a prototype into a production-ready, cross-platform, privacy-first
application for visualising and safely organising files on local disks.

Vision
------
Provide non-technical users and power users with a safe, auditable, and
actionable tool to reclaim disk space and organise files. The app will
prioritise safety (dry-run previews + atomic backups), privacy (file content
never leaves the machine unless explicitly configured), and extensibility
(pluggable AI recommendation providers).

Principles
- Safety-first: dry-run previews, automatic backups, and simple undo flows.
- Privacy-first: no default cloud calls, opt-in model usage, and explicit consents.
- Incremental: support resumable, incremental scans so large disks are practical.
- Extensible: clean plugin interface for model providers and future analysis modules.

Success Criteria
- Reliable incremental scanning that can resume and prune indexes.
- Accurate duplicate detection (size + sample-hash + full-hash) with configurable thresholds.
- Clear visualisation (treemap/sunburst) that helps users decide what to keep.
- Safe preview/execute/undo lifecycle with audit logs and recoverable backups.
- Integration points for local/cloud model providers with deterministic fallback.
- Cross-platform packaging (macOS, Windows, Linux) and automated CI builds.

MVP Feature List (target for initial public release)
- Scan directories and detect duplicates with sample/full hashing.
- Lightweight visualisation (treemap) and drill-down by folder.
- Create suggestion previews and a non-destructive dry-run UI.
- Execute organise operations with backup to `backend/ops_backups` and undo.
- Basic provider integration with deterministic fallback (ci_dummy).
- Tests and CI pipeline (pytest + Playwright visual smoke tests).

Roadmap & Phases (summary)
- Phase 0 — Product definition & acceptance criteria (1 week)
- Phase 1 — API stabilization and OpenAPI spec (2 weeks)
- Phase 2 — Data model, index migration & pruning (2 weeks)
- Phase 3 — Scanner performance, resumable scans, and background jobs (2–3 weeks)
- Phase 4 — Duplicate engine improvements and fuzzy similarity (2–3 weeks)
- Phase 5 — Organisation engine, transactional ops and undo (2 weeks)
- Phase 6 — AI recommendation layer (pluggable; async job mode) (2–3 weeks)
- Phase 7 — UX redesign, visual disk map & accessibility (3–4 weeks)
- Phase 8 — Packaging, CI/CD, cross-platform builds, and releases (2 weeks)
- Phase 9 — Documentation, onboarding, beta release and feedback (2 weeks)
- Phase 10 — Hardening, security review, long-term maintenance (2–4 weeks)

Key Deliverables
- OpenAPI definition for backend APIs.
- Solid scanning/indexing module with WAL/SQLite tuning and pruning tools.
- Modular duplicate detection engine with pluggable strategies.
- Safe ops store with atomic backups and undo capability.
- Frontend visualiser (treemap / sunburst) and accessible controls.
- Integration examples for model providers (ci_dummy, modelito, example Ollama wrapper).
- CI pipelines that run unit tests, visual tests, and produce release artifacts.

Technical Workstreams
- Backend refactor: split `backend/app.py` into controllers, services, and background workers.
- Index: harden `backend/scan_index.py`, add pruning and stats endpoints.
- Scanner: implement resumable incremental scans and concurrent hashing.
- Ops-store: ensure atomic backup semantics and retention policies.
- AI layer: `backend/model_client.py` to support async suggestions and provider health checks.
- Frontend: modular components, lazy-load D3, Playwright tests for visual regression.

Testing & CI
- Unit tests for scanner, index, and fs preview helpers.
- Integration tests for preview → execute → undo flows.
- Playwright visual smoke tests for the treemap and preview modal.
- GitHub Actions to gate builds and produce PyInstaller / Docker artifacts.

Packaging & Distribution
- PyInstaller single-binary for desktop users (macOS/Windows/Linux where feasible).
- Docker image for advanced or server-hosted use.
- Release artifacts published to GitHub Releases.

Risks & Mitigations
- Data loss risk: mitigate via dry-run defaults, mandatory backups for destructive ops, and multi-stage execution.
- Slow AI providers: async job model + deterministic fallback.
- Scale: use sampling, incremental index pruning, and user-configured limits.

Dependencies & Integrations
- Optional: Redis/RQ for background workers; cloud model providers (user opt-in).
- Required dev tooling: pytest, Playwright, Prettier for frontend formatting.

Metrics & Monitoring
- Scan throughput (files/sec), index size, and time-to-first-duplicates.
- False-positive rate for duplicate groups (evaluated during beta).
- User success metrics: completed organise ops, undo rate, feedback.

Immediate Next Steps
1. Start Phase 0: produce a product spec and acceptance criteria (this is in progress).
2. Create a PR with `docs/PROJECT_PLAN.md` and `docs/PHASE_0_PRODUCT_SPEC.md`.
3. Create issues for Phase 1 (API spec), Phase 2 (index hardening), and UX spike for Phase 7.

References
- `docs/MODEL_INTEGRATION.md` — provider contract and examples.
- `backend/scan_index.py` — index design and rebuild logic.
- `backend/fs_ops.py` — dry-run preview helpers.

---

This file is the canonical roadmap for ongoing work. Update it as priorities change.
