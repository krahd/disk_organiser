Disk Organiser
=============

Disk Organiser is a small prototype tool to help users visualise and safely
organise files on their local filesystem. It emphasises:

- Data-safety: all organise operations create backups so actions can be
  reviewed or undone.
- Extensibility: optional AI model providers can be plugged in for
  suggestion-based workflows.
- Simplicity: minimal static frontend + a Flask API backend for easy local use.

Goals
-----

- Provide a friendly UI for visualising disk usage and finding duplicates.
- Offer deterministic heuristics (safe defaults) and optional ML-assisted
  suggestions when a provider is configured.
- Keep the code simple and well-documented so contributors can extend it.
