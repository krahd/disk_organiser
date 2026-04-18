# Copilot Workspace Instructions

## Project Overview
This application helps users organise their hard drive by providing:
- Visualisation of the hard drive
- Search for repeated files
- Tools to create an internal organisation tailored to the user's needs

It supports both local models (via Ollama) and cloud-based models (Claude, GPT, etc.) if the user provides an API key. The backend logic is written in Python, and the interface is web-based, following the style of the mail_summariser project.

## Principles
- **User-centric design:** Prioritise non-technical users and in-app simplicity.
- **Minimal editorial presentation:** Follow the restrained, project-led structure of https://tomas-laurenzo.squarespace.com.
- **Link, don’t embed:** Reference documentation and code where possible, avoid duplication.
- **Separation of concerns:** Keep backend logic (Python) and frontend (web) clearly separated.
- **Extensibility:** Design for easy addition of new models or visualisation features.

## Conventions
- Use Python for backend logic and web technologies (HTML/CSS/JS) for the frontend.
- Support both local and remote AI models for file analysis and recommendations.
- Follow the UX and design patterns established in the mail_summariser project.

## Build & Run
- Backend: Python (recommend venv or poetry for dependencies)
- Frontend: Vanilla web (no React/Vite)
- To run locally, start the Python backend and open the web interface in a browser.

## Potential Pitfalls
- Model selection: Ensure the user can easily switch between local and remote models.
- File system access: Handle permissions and large directory trees gracefully.
- Cross-platform compatibility: Test on macOS, Windows, and Linux.

## Example Prompts
- "Visualise my hard drive and suggest an organisation structure."
- "Find all duplicate files larger than 100MB."
- "Switch to using Claude for file analysis."

## Next Steps
- Consider creating agent-customizations for specific workflows (e.g., duplicate search, visualisation, user-guided organisation).
- Propose hooks for model selection and user preferences.

---
For more details, see the codebase and reference the mail_summariser project for UI/UX patterns.
