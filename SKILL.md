---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 2d199c0a34e4d65bd15eb413952e1e31_30441053d64711f19fe5525400638852
    ReservedCode1: tEqMBHyCUR5CMt23EAzXxvyH4naF35SicXTKOmoyCX0r4f0Yk1NjCWEOTt8lnWDXWj16eX9rD7iPUZUZKMeZWSSJmt7HImVxfq3zwOFQE1gXguKUEWs90XMwdx9zJ5Y8ps/V56DtTZWS0sS/rZk4ZBwxmQpAUm0obsv1HI5e+OILPKybc7fF4gB2S+w=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 2d199c0a34e4d65bd15eb413952e1e31_30441053d64711f19fe5525400638852
    ReservedCode2: tEqMBHyCUR5CMt23EAzXxvyH4naF35SicXTKOmoyCX0r4f0Yk1NjCWEOTt8lnWDXWj16eX9rD7iPUZUZKMeZWSSJmt7HImVxfq3zwOFQE1gXguKUEWs90XMwdx9zJ5Y8ps/V56DtTZWS0sS/rZk4ZBwxmQpAUm0obsv1HI5e+OILPKybc7fF4gB2S+w=
---



# skill-forge

Most skills fail for one boring reason: the agent never knows when to load them.
This skill builds skills that fire, and scores them on the five dimensions that
predict adoption — not on how long the prompt is.

## When to use

- "Write me a skill that converts PDF invoices to CSV."
- "Turn this workflow into a reusable skill."
- "Why doesn't my skill ever trigger?"
- "Review my SKILL.md before I publish it."
- "I want to open-source this skill — is it any good?"
- 中文触发：帮我写个 skill / 做一个技能 / 我的技能不生效 / 帮我看看这个 SKILL.md

Do **not** use it for writing MCP servers, system prompts, or plain
documentation. Those are different artifacts with different rules.

## The one rule that matters

A skill is loaded by **description matching**, not by being on disk.
If the description does not contain (a) what it does and (b) the exact words a
user would say, the skill is dead weight. Write the description first, and write
it as if it were the only thing the model will ever read.

## Workflow

1. **Converge the requirement.** Extract three things; if any is missing, ask
   exactly one question covering all gaps, then proceed with a stated assumption:
   - **Trigger**: what will the user literally type?
   - **Input**: what artifact arrives (file, path, pasted text, URL, nothing)?
   - **Done**: what does success look like, and who checks it?

2. **Pick the shape.** Do not overbuild. Choose the lightest one that works:

   | Shape | Use when | Ships |
   |---|---|---|
   | Instruction only | Judgment work, no deterministic output | `SKILL.md` |
   | Instruction + script | Any parsing, conversion, counting, formatting | `scripts/<name>.py` |
   | Instruction + resources | Reference material > 100 lines | `resources/*.md` |

   Anything mechanical belongs in a script. A model should not be doing string
   surgery that `str.replace` does correctly every time.

3. **Write `SKILL.md`.** Enforce these hard constraints:

   ```
   name          lowercase, digits, hyphens only; <= 64 chars; == directory name
   description   <= 1024 chars; third person; states WHAT + WHEN; names real artifacts
   body          40–500 lines; numbered workflow; output contract; guardrails
   ```

4. **Ship the script** (if the skill has one). Rules for `scripts/`:
   - stdlib only, or declare the dependency in the first line of the body;
   - accept a path argument, never hardcode absolute paths;
   - print a diff or a summary, and exit non-zero on failure;
   - make it idempotent — running twice must not double-apply.

5. **Score it, then fix the errors.**

   ```bash
   python scripts/skillforge.py score <skill-dir>
   python scripts/skillforge.py score <skill-dir> --json
   ```

   Loop until `errors == 0` and score >= 85. Do not hand-wave a 60.

6. **Report** in the contract below. Never claim a score you did not run.

## Scoring model

| Dimension | Pts | What it really measures |
|---|---|---|
| Structure | 25 | Front matter validity, name/directory match, description length |
| Triggerability | 25 | Does the description contain an action + an explicit "use when" |
| Executability | 20 | Are there steps, working refs, a real command, sane length |
| Reliability | 15 | Examples, guardrails, output contract |
| Discoverability | 15 | README, LICENSE, copy-paste install line |

Grades: A >= 90, B >= 75, C >= 60, D < 60. Below 75 the skill is not ready.

## Output

Return exactly this, in this order:

1. **Path** — absolute path of the generated skill directory.
2. **Files** — each file created, one line each.
3. **Description** — the frontmatter description, quoted verbatim.
4. **Score** — the score line from `skillforge.py`, pasted, plus remaining warnings.
5. **Next step** — the single highest-leverage fix if the score is under 90.

## Guardrails

- **Never invent a score.** Run the CLI, paste the output.
- **Never write outside the target skill directory** without asking.
- **Do not pad the body.** If a section has no content, delete the heading; an
  empty "## Examples" heading scores worse than none.
- **Stop and ask** if the requirement implies a destructive action (deleting,
  overwriting, publishing, pushing) — those are the user's call, not the skill's.
- **Do not copy a well-known skill's text.** Reuse its structure, never its prose.

## Anti-patterns that kill adoption

| Smell | Why it fails | Fix |
|---|---|---|
| Description: "A powerful skill for productivity" | Nothing matches it | Name the input and the verb |
| 800-line SKILL.md | Loaded into context on every trigger | Move reference into `resources/` |
| No example | Model improvises output shape | One input→output pair |
| Script with hardcoded `/home/me/...` | Breaks on every other machine | Take a path argument |
| Skill that needs 5 env vars to run | Nobody gets past install | Degrade gracefully or drop it |
| README without an install line | Highest-leverage star killer | One copy-paste block at the top |

## Examples

**Input:** "I want a skill that renames photos by EXIF date."

**Output:**

```
photos-by-date/
├── SKILL.md
├── README.md
├── LICENSE
└── scripts/sort_photos.py
```

Frontmatter:

```yaml
name: photos-by-date
description: Renames and sorts photo files into YYYY/MM folders using EXIF capture date, falling back to file mtime when EXIF is absent. Use when the user asks to organise, rename, or sort photos by the date they were taken.
```

Score after one fixing pass: `87/100 grade B` — the remaining warning was
`no examples/ directory`, so an `examples/` folder with one before/after tree
was added, reaching 92.

## Verification

```bash
python scripts/skillforge.py score . --min-score 85
echo $?   # 0 = shippable
```

Use it in CI so a PR that breaks the description cannot merge:

```yaml
- run: python scripts/skillforge.py score ./my-skill --min-score 85
```
*（内容由AI生成，仅供参考）*
