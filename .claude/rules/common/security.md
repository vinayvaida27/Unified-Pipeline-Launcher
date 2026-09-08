# ECC security review

Adapted from ECC 2.2.1 `common/security.md`. Follow [AGENTS.md](../../../AGENTS.md).

Review application trust boundaries separately from coding-agent hooks, MCP
servers, permissions, and destinations. Use synthetic inputs and local static
scans. Reports contain locations and remediation, never secret values.

Vulnerability scans cover the development lock and deployed distribution
metadata separately. Dependency compatibility checks are not vulnerability
scans. Preserve scientific dependency pins until an upgrade is explicitly
selected and tested. Do not enable an integration merely because ECC ships it.
