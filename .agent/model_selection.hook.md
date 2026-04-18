# Model Selection Hook

## Purpose
Allows users to choose between local (Ollama) and remote (Claude, GPT, etc.) models for file analysis and recommendations.

## Usage
- Example prompt: "Switch to using Claude for file analysis."
- The hook presents available models and updates the backend accordingly.

## Implementation Notes
- Backend maintains model selection state and API keys securely.
- Web UI provides a simple dropdown or toggle for model selection.
- Follows minimal, user-friendly design.

## Extensibility
- Add support for more models as needed.
- Integrate with agent workflows for context-aware model switching.

---
See .github/copilot-instructions.md for project-wide principles and conventions.
