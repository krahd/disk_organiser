# Duplicate Search Agent Customization

## Purpose
Automates the process of finding duplicate files on the user's hard drive, with options to filter by size, type, or location.

## Usage
- Example prompt: "Find all duplicate files larger than 100MB."
- The agent will scan the specified directories, compare file hashes, and present a summary of duplicates.

## Implementation Notes
- Uses Python backend for file system traversal and hashing.
- Results are presented in the web UI, following the minimal, user-friendly style.
- Supports both local and remote model analysis for advanced duplicate detection (e.g., fuzzy matching).

## Extensibility
- Add options for user-guided review before deletion.
- Integrate with model selection hooks for smarter duplicate detection.

---
See .github/copilot-instructions.md for project-wide principles and conventions.
