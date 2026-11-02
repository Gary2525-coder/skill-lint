---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 2d199c0a34e4d65bd15eb413952e1e31_31d32c83d64711f1a97752540064ee0f
    ReservedCode1: +vFR1q75xKoxqwzOyIrM3tVFKem3m1OQz1RSRYeXjMCyh/vgki635CWZWBzVZKp9X3JDB3AqZX9cs129pqDcDDYlfHa4erY56dGEmZBxTDq4RtAe+7L6GB0ofbH8hnTleSyNPR9iCHKVryFLt8ewD1EqYqOEASRu9bOvyUizhNs2ACZqCa0+4Gmn/ik=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 2d199c0a34e4d65bd15eb413952e1e31_31d32c83d64711f1a97752540064ee0f
    ReservedCode2: +vFR1q75xKoxqwzOyIrM3tVFKem3m1OQz1RSRYeXjMCyh/vgki635CWZWBzVZKp9X3JDB3AqZX9cs129pqDcDDYlfHa4erY56dGEmZBxTDq4RtAe+7L6GB0ofbH8hnTleSyNPR9iCHKVryFLt8ewD1EqYqOEASRu9bOvyUizhNs2ACZqCa0+4Gmn/ik=
---

# Contributing

The bar for a new check is simple: it must catch a failure that has actually
shipped in a real skill. Speculative linting creates noise, and noise gets a
linter uninstalled.

## Add a check

1. Pick the dimension it belongs to in `scripts/skillforge.py` (`Structure`,
   `Triggerability`, `Executability`, `Reliability`, `Discoverability`).
2. Use the `add(level, code, dim, points, max_points, message, fix)` helper.
   Every warning needs a `fix` — a check without a suggested fix is a complaint,
   not a tool.
3. Never change the total of a dimension. Rebalance points inside it instead.
4. Add a failing fixture under `examples/` so the check is testable.

## Add an example

Examples are how people decide whether to trust the score. They must be real:
a real input, a real command, a real output block. Placeholder examples score
lower on purpose — the scorer treats them as missing.

## Rules

- Standard library only in `scripts/`. No `pip install`, ever.
- Every script takes a path argument. No hardcoded absolute paths.
- Read-only by default; anything that writes needs a `--dry-run`.
- Keep `SKILL.md` under 500 lines. Detail goes in `resources/`.

## Before you open a PR

```bash
python scripts/skillforge.py score . --min-score 85
python scripts/skillforge.py score examples/photos-by-date --min-score 85
```

CI runs both. A red build means the change made the skill worse, not that the
test is wrong.
*（内容由AI生成，仅供参考）*
