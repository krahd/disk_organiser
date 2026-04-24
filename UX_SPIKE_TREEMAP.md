# UX Spike — Treemap Prototype

Date: 2026-04-18
Author: GitHub Copilot (UX spike)

What I built
- A small, self-contained treemap prototype: `docs/demo/treemap_spike.html` + `docs/demo/treemap_spike.js`.
- Uses hard-coded sample data to validate visual encoding, tooltips, and click interactions.

Goals of the spike
- Validate that a treemap provides quick visual affordance for identifying large folders and potential duplicates.
- Test simple interactions: hover tooltips and click-to-see-details.
- Confirm lazy-loading D3 (the main app already lazy-loads d3) is acceptable.

Findings
- Treemap communicates relative sizes immediately; large folders stand out.
- Hover tooltips + a simple details modal (or side-panel) are sufficient for MVP.
- For large datasets, consider progressive loading (summary > detail) or sampling.

Next steps / recommendations
1. Integrate treemap into the main UI (`frontend/main.js`) behind the Visualisation tab. Connect `POST /api/visualisation` to fetch hierarchical data.
2. Add a side-panel detail view instead of `alert()` for better UX and to show suggested actions (preview suggestions from duplicates API).
3. Add keyboard accessibility and focus outlines for keyboard navigation.
4. Add Playwright visual tests asserting treemap renders and tooltip shows on hover.
5. Consider performance: for very large trees, aggregate low-value nodes and provide a "show more" drill-down.

Files
- `docs/demo/treemap_spike.html`
- `docs/demo/treemap_spike.js`

