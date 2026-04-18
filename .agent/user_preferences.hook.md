# User Preferences Hook

## Purpose
Stores and manages user preferences for the application, such as default model, visualisation style, and organisation schemes.

## Usage
- Example prompt: "Set my default model to Ollama."
- The hook updates preferences and ensures they persist across sessions.

## Implementation Notes
- Backend securely stores preferences (e.g., in a config file or database).
- Web UI provides accessible controls for updating preferences.
- Minimal, non-intrusive design.

## Extensibility
- Add more preference options as features grow.
- Integrate with agent workflows for personalised experiences.

---
See .github/copilot-instructions.md for project-wide principles and conventions.
