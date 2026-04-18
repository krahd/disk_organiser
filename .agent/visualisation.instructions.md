# Visualisation Agent Customization

## Purpose
Provides visual representations of the user's hard drive, such as directory trees, file type distributions, and storage usage heatmaps.

## Usage
- Example prompt: "Visualise my hard drive and suggest an organisation structure."
- The agent generates interactive or static visualisations in the web UI.

## Implementation Notes
- Backend gathers file system data and prepares it for frontend rendering.
- Frontend uses simple, accessible charts (e.g., D3.js, SVG, or HTML/CSS) in a minimal style.
- Follows the design and UX patterns of mail_summariser.

## Extensibility
- Add drill-down features for deeper exploration.
- Integrate with model selection for AI-driven organisation suggestions.

---
See .github/copilot-instructions.md for project-wide principles and conventions.
