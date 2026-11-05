---
name: launcher-performance-engineer
description: Profile, refactor, benchmark, and optimize Windows Python/Qt/Streamlit launcher applications using DSA, algorithmic optimization, concurrency, caching, memory management, and performance engineering.
---

# Launcher performance engineering

Profile the real launcher path before changing code. Preserve localhost-only
binding, isolated browser sessions, process supervision, registry validation,
runtime repair, and existing UI behavior.

Use the standard library and tools already present in the repository. Measure
cold and warm startup separately, record the exact command and workload, and
never invent results. Prefer lazy imports, bounded work, incremental scans,
and existing caches over new dependencies or broad rewrites.

Before editing a function, inspect every caller and its tests. Keep public
interfaces stable, invalidate caches from file metadata, and avoid caching
security decisions or mutable registry data without a clear invalidation rule.
Do not add background network work or automatic package upgrades to ordinary
startup.

Run focused tests after each optimization, then the widest available suite.
Report measured before/after values, unverified Windows/network-drive cases,
and any remaining bottleneck. A new optimization is complete only when it has
an evidence-backed benefit or is removed.
