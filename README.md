# skill-lint

**Build Agent Skills that actually fire — then score them before you ship.**

Most skills are never loaded. Not because they're bad, but because the agent has
no idea *when* to load them. `skill-lint` gives you two things:

1. A skill that turns a one-line requirement into a complete, publishable skill folder.
2. A CLI that scores any skill on the five things that decide adoption — including
   the `description` trap that silently kills 90% of them.

```console
$ python scripts/skilllint.py score ./my-skill

skill-lint  ·  ./my-skill
score 67/100   grade C

  Structure   25/25  ##########
  Trigger     17/25  #######...
  Execute     14/20  #######...
  Reliab.      6/15  ####......
  Discover     5/15  ###.......

[!] T2  description never says WHEN to use it — this is the #1 reason skills never fire.
        fix: Append: 'Use when the user asks to …'.
[~] D2  no LICENSE — companies can't adopt it.
[~] D3  no install instructions found in README.
        fix: Give a copy-paste install line — the single biggest star factor.
[~] E3  no command block.
[~] R1  no examples — the agent has no gold standard to imitate.

11 passed · 8 warnings · 1 errors
blocked: fix errors before publishing.
```

Fix those, run it again, ship. That's the whole loop.

---

## Install

```bash
git clone https://github.com/<your-name>/skill-lint.git
mkdir -p ~/.claude/skills && cp -r skill-lint ~/.claude/skills/
```

Works with Claude Code, Codex, Cursor, and anything else that reads the
`SKILL.md` convention (YAML front matter + markdown body + optional `scripts/`).
Nothing else to configure, no API key, no dependencies.

## Use

Say this to your agent:

> Write me a skill that converts PDF invoices into a CSV ledger.

It converges the requirement, picks the right shape (instructions only vs. plus
a script), writes `SKILL.md`, ships the script, scores it, and reports back with
the score and the highest-leverage fix left.

Or do it from the shell:

```bash
python scripts/skilllint.py new "convert pdf invoices to csv"   # scaffold
python scripts/skilllint.py score ./pdf-invoices-to-csv         # audit
python scripts/skilllint.py score ./pdf-invoices-to-csv --json  # machine-readable
python scripts/skilllint.py score ./my-skill --min-score 85     # CI gate, exit 1 on fail
```

## What it scores

| Dimension | Pts | The question it answers |
|---|---|---|
| **Structure** | 25 | Is the front matter valid, does `name` match the folder, is `description` the right length? |
| **Triggerability** | 25 | Does the description name an action *and* an explicit "use when"? Is there a trigger section? |
| **Executability** | 20 | Are there real steps, working file references, a runnable command, sane body length? |
| **Reliability** | 15 | Examples, guardrails, and a defined output contract? |
| **Discoverability** | 15 | README, LICENSE, and a copy-paste install line? |

Grades: **A** ≥ 90 · **B** ≥ 75 · **C** ≥ 60 · **D** < 60.
Under 75, don't publish — you're asking strangers to debug your prompt.

## The trap it catches

```yaml
# 0 points on Triggerability
description: A powerful skill for productivity workflows.

# 25 points — action + trigger + concrete artifact
description: Converts PDF invoices into a CSV ledger with date, vendor, and total columns. Use when the user asks to extract, tabulate, or reconcile invoice data from PDFs.
```

The second one can be found by a model. The first one cannot, no matter how good
the body is. This is the single highest-return edit in the entire skill ecosystem,
and almost nobody does it.

## Zero-install check

```bash
curl -sO https://raw.githubusercontent.com/<your-name>/skill-lint/main/scripts/skilllint.py
python skilllint.py score ./my-skill
```

## CI

```yaml
- uses: actions/checkout@v4
- run: python scripts/skilllint.py score ./my-skill --min-score 85
```

A PR that guts your description now fails the build instead of quietly making
the skill unreachable.

## Companion: the human half

The CLI grades the machine half — routing, structure, contract. The other half
is whether a human scrolling GitHub believes it in four seconds: one-line pitch,
a pasted terminal session, a copy-paste install block, MIT license. `skill-lint`
scores the last two; write the first two yourself.

## License

MIT
*（内容由AI生成，仅供参考）*
