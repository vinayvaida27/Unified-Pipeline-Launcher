---
name: python-to-streamlit
description: Convert a Python script into a registered Streamlit application for Unified Pipeline Launcher. Use when a user asks to turn a .py workflow, CLI, or analysis script into a launcher app.
---

# Python to Streamlit

Convert the user's Python workflow into a small, usable Streamlit application
that can be registered in this repository's launcher. Preserve the scientific or
business logic unless the user asks to change it. Do not accept or publish
laboratory data, patient data, credentials, or other sensitive inputs.

## Required intake

Before writing or changing application code, ask exactly these five brief
questions in one message. Do not begin implementation until the answers provide
enough detail to make the app safe and useful.

1. **Input:** What files, pasted values, or user selections should the app accept? Include example formats and required columns or fields.
2. **Output:** What should the app display, download, save, or pass to another step? Include the expected format and a small example.
3. **Workflow:** What does the existing `.py` file do, which function or command starts it, and what should happen when it fails?
4. **Parameters:** Which settings must users configure, with defaults, allowed values, units, and validation rules?
5. **App details:** What name, short description, category, icon preference, and privacy or data-retention constraints should the launcher show?

If the user supplies all five answers in the initial request, restate the
understood contract briefly and continue without repeating the questions.

## Implementation

- Inspect the source script before modifying it. Extract reusable, side-effect
  controlled functions instead of placing CLI parsing, file-system writes, or
  computation directly in Streamlit callbacks.
- Use the existing `apps/app_template` layout: `app.py`, `requirements.txt`, and
  `assets/icon.svg`. Add the new app to `apps/apps.json` with a unique ID,
  semantic version, display order, description, category, and icon path.
- Keep user-provided paths and generated outputs within the app's selected or
  configured directories. Validate input formats before processing and give
  clear, actionable errors.
- Use Streamlit widgets that match the answer: uploaders for files, structured
  controls for parameters, progress/status while a long task runs, and download
  buttons for generated results. Never start a server, invoke `uv`, or install
  packages during normal app use.
- Keep dependencies minimal and list only runtime packages required by the new
  app in its `requirements.txt`. Do not alter shared scientific package pins or
  unrelated applications.
- Use the launcher defaults: bind only to `127.0.0.1`, use a dynamic port, and
  keep the app headless. Do not add external network access unless the user
  explicitly requests it.

## Completion checks

- Run the app's direct Python/import checks and focused tests for the extracted
  logic.
- Verify the registry discovers the app and that its declared entrypoint,
  requirements file, and icon path stay inside the app folder.
- Run the public quality gate when app assets or launcher registration changes.
- Report the five answered requirements, files created or changed, validation
  performed, and any remaining data/privacy assumptions.
