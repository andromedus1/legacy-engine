---
id: feature-decision-data-currency-runtime-alignment
kind: story
stage: done
tags: [infra]
parent: feature-decision-data-currency
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Align the local and CI Python runtime contract

## Brief

Pin the maintainer checkout to Python 3.13, bound package support to Python 3.11–3.13, test both
the lower bound and maintainer pin in CI, and document the optional discovery stack honestly so a
fresh contributor checkout has the same definition of green as CI.

## Implementation

Implement Unit 1 in the parent feature's `## Implementation Units` section. Preserve unrelated
`uv.lock` edits; only reconcile its Python constraint if the package tool requires it and the
existing change can be retained.

## Implementation notes

- Execution capability: frontier/high; runtime reproducibility crosses package metadata, local
  tooling, CI, and the optional scientific stack.
- Review weight: standard (caller).
- Files changed: `pyproject.toml`, `.python-version`, `.github/workflows/ci.yml`,
  `CONTRIBUTING.md`, and `tests/test_runtime_contract.py`.
- Tests added: two repository-contract tests bind the package range, maintainer pin, CI matrix,
  contributor runtime, and honest optional-discovery wording.
- Simplification: one matrix now proves both package boundaries; the contributor command uses the
  same 3.13 pin as CI.
- Discrepancies from design: `uv.lock` was intentionally not touched because it carried the user's
  unrelated pre-existing modification and the contract is fully expressed by package metadata.
- Adjacent issues parked: none.

## Verification

- `.venv/bin/python -m pytest -q tests/test_runtime_contract.py` — 2 passed.
