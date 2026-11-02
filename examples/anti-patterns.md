# Anti-patterns

Each row is a real shape that ships constantly and fails constantly. The left
column is what the scorer flags; the right column is what to write instead.

## 1. The invisible description

```yaml
# score: Trigger 0/25
description: A powerful skill for productivity workflows.
```

No verb a model can match, no situation, no object. Write:

```yaml
description: Converts PDF invoices into a CSV ledger with date, vendor, and total columns. Use when the user asks to extract, tabulate, or reconcile invoice data from PDFs.
```

## 2. The 800-line prompt

Anything that must be present on every load belongs in `SKILL.md`. Everything
else — full API references, long style guides, giant lookup tables — belongs in
`resources/` and gets read only when needed. A bloated body does not make the
skill better, it makes the model skim.

## 3. The missing output contract

"It helps with X" is not an output. State the shape:

```
Return: what was produced, where it was written, and what the user should do next.
```

## 4. The homemade parser in prose

If the operation is mechanical — parsing, counting, formatting, converting —
ship a script. Do not ask a language model to do string surgery that
`str.replace` does correctly every single time.

## 5. The unwritten guardrail

Every skill that touches files, money, or a public surface needs one line about
what it must never do. Without it, the first bad run is also the last install.

## 6. The README without an install line

The most common reason a genuinely good skill gets three stars. Put the
copy-paste block above the fold, before the feature list.
