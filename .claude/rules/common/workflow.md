# ECC workflow for this repository

Adapted from ECC 2.2.1 `common/development-workflow.md`, `common/testing.md`,
and `common/code-review.md`. Project requirements live in [AGENTS.md](../../../AGENTS.md).

1. Inspect the actual code and callers; describe a concrete, minimal fix.
2. Run a focused reproducer before changing production logic; record RED evidence.
3. Apply the root-cause fix and rerun the same test plus relevant existing tests.
4. Obtain independent review of the actual diff. Address confirmed findings.
5. Record commands, exit codes, measured results, and NOT RUN acceptance scenarios.
6. Present an explicit file list and final report before committing or pushing.

Use existing helpers and the standard library first. Additional architecture,
agents, configuration, and dependencies require a concrete need. Do not copy
JavaScript examples or unrelated ECC workflows into this application.
