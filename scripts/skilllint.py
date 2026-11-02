#!/usr/bin/env python3
"""
skill-lint — lint and score an Agent Skill before you ship it.

Usage:
    python scripts/skilllint.py score ./my-skill
    python scripts/skilllint.py score ./my-skill --json
    python scripts/skilllint.py score ./my-skill --min-score 80   # CI gate
    python scripts/skilllint.py new "convert invoices to csv"      # scaffold

Exit codes:
    0  passed (score >= min-score, no errors)
    1  failed (score below threshold or lint errors)
    2  bad usage / unreadable skill
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

MAX_DESC = 1024
MAX_NAME = 64
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

ACTION_WORDS = [
    "generate", "create", "build", "convert", "extract", "review", "fix",
    "analyze", "analyse", "write", "summarize", "summarise", "translate",
    "scaffold", "lint", "score", "audit", "refactor", "render", "export",
    "compare", "validate", "optimize", "optimise", "debug", "test",
    "sort", "rename", "organise", "organize", "move", "merge", "split",
    "clean", "format", "parse", "normalize", "normalise", "plan", "check",
    "生成", "创建", "转换", "提取", "审查", "修复", "分析", "编写", "总结",
    "翻译", "重构", "导出", "校验", "对比", "优化", "调试", "检查", "整理", "重命名",
]

TRIGGER_PHRASES = [
    "use when", "use this", "use it when", "when the user", "when you need",
    "trigger", "should be used", "invoke when", "for requests",
    "当用户", "适用于", "使用场景", "触发",
]

CONCRETE_NOUNS = [
    "file", "files", "pdf", "docx", "xlsx", "csv", "json", "yaml", "image",
    "screenshot", "video", "audio", "commit", "pull request", "pr", "issue",
    "api", "endpoint", "schema", "database", "sql", "log", "logs", "test",
    "tests", "repo", "repository", "readme", "skill", "prompt", "deck",
    "slide", "article", "email", "invoice", "chart", "diagram", "table",
    "文档", "表格", "图片", "截图", "视频", "日志", "代码", "仓库", "接口",
    "数据库", "发票", "文章", "邮件", "图表", "幻灯片", "技能",
]

GUARDRAIL_WORDS = [
    "do not", "don't", "never", "must not", "avoid", "only if", "confirm",
    "禁止", "不要", "严禁", "必须确认", "仅在", "只有",
]

OUTPUT_WORDS = [
    "output", "return", "report", "respond with", "final answer", "summary of results",
    "输出", "返回", "报告", "汇报", "最终结果",
]

FIRST_PERSON = re.compile(r"(^|\n)\s*(i can|i will|i'll|you can|you should|我可以|你可以)\b", re.I)
PATH_REF = re.compile(r"(scripts/[\w./-]+|resources/[\w./-]+|assets/[\w./-]+|references/[\w./-]+)")


# ---------------------------------------------------------------- frontmatter

def split_frontmatter(text: str) -> tuple[dict, str, bool]:
    """Minimal YAML front matter reader (top-level scalars + block scalars)."""
    if not text.startswith("---"):
        return {}, text, False
    lines = text.splitlines()
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            end = i
            break
    if end is None:
        return {}, text, False

    meta: dict[str, str] = {}
    i = 1
    while i < end:
        line = lines[i]
        m = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, value = m.group(1), m.group(2).strip()
        if value in ("|", ">", "|-", ">-", "|+", ">+"):
            block = []
            i += 1
            while i < end and (lines[i].startswith(" ") or lines[i].strip() == ""):
                block.append(lines[i].strip())
                i += 1
            joiner = "\n" if value.startswith("|") else " "
            meta[key] = joiner.join(b for b in block).strip()
            continue
        value = re.sub(r"^[\"']|[\"']$", "", value)
        meta[key] = value
        i += 1

    body = "\n".join(lines[end + 1:]).lstrip("\n")
    return meta, body, True


# ---------------------------------------------------------------- checks

@dataclass
class Finding:
    level: str      # OK | WARN | ERROR
    code: str
    dim: str
    points: float
    max_points: float
    message: str
    fix: str = ""


@dataclass
class Report:
    path: str
    score: int = 0
    grade: str = "D"
    dims: dict = field(default_factory=dict)
    findings: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    lines: int = 0

    def as_dict(self):
        return {
            "path": self.path,
            "score": self.score,
            "grade": self.grade,
            "dimensions": {k: {"got": round(v[0], 1), "max": v[1]} for k, v in self.dims.items()},
            "findings": [
                {"level": f.level, "code": f.code, "dimension": f.dim,
                 "points": f.points, "max": f.max_points,
                 "message": f.message, "fix": f.fix}
                for f in self.findings
            ],
            "frontmatter": self.meta,
            "body_lines": self.lines,
        }


def check(skill_dir: Path) -> Report:
    skill_dir = Path(skill_dir).resolve()
    rep = Report(path=str(skill_dir))
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.exists():
        rep.findings.append(Finding("ERROR", "S0", "Structure", 0, 25,
                                    "SKILL.md not found — a skill without SKILL.md is invisible to the agent.",
                                    "Create SKILL.md with a YAML front matter block."))
        rep.dims = {"Structure": (0, 25), "Triggerability": (0, 25), "Executability": (0, 20),
                    "Reliability": (0, 15), "Discoverability": (0, 15)}
        rep.grade = "D"
        return rep

    text = skill_md.read_text(encoding="utf-8", errors="replace")
    meta, body, has_fm = split_frontmatter(text)
    rep.meta = {k: (v[:120] + "…" if len(v) > 120 else v) for k, v in meta.items()}
    body_lines = body.splitlines()
    rep.lines = len(body_lines)
    low_body = body.lower()

    def add(level, code, dim, pts, mx, msg, fix=""):
        rep.findings.append(Finding(level, code, dim, pts, mx, msg, fix))
        return pts

    # ---------------- Structure (25)
    s = 0.0
    s += add("OK" if has_fm else "ERROR", "S1", "Structure", 5 if has_fm else 0, 5,
             "YAML front matter present." if has_fm else "Missing YAML front matter (--- ... ---).",
             "" if has_fm else "Start the file with ---, name:, description:, then ---.")

    name = str(meta.get("name", "")).strip()
    name_ok = bool(name) and len(name) <= MAX_NAME and bool(NAME_RE.match(name))
    s += add("OK" if name_ok else "ERROR", "S2", "Structure", 5 if name_ok else 0, 5,
             f"name is valid: {name}" if name_ok else f"name missing or invalid: {name!r}",
             "" if name_ok else "Lowercase letters/digits/hyphens only, <=64 chars, e.g. pdf-table-extractor.")

    dir_match = name_ok and name == skill_dir.name
    s += add("OK" if dir_match else "WARN", "S3", "Structure", 5 if dir_match else 2, 5,
             "name matches directory name." if dir_match else f"name {name!r} != directory {skill_dir.name!r}.",
             "" if dir_match else "Rename the directory to match name, or fix name.")

    desc = str(meta.get("description", "")).strip()
    s += add("OK" if desc else "ERROR", "S4", "Structure", 5 if desc else 0, 5,
             "description present." if desc else "Missing description — the agent has nothing to match on.",
             "" if desc else "One or two sentences: what it does + when to use it.")

    desc_len_ok = 40 <= len(desc) <= MAX_DESC
    if len(desc) > MAX_DESC:
        s += add("ERROR", "S5", "Structure", 0, 5, f"description is {len(desc)} chars (max {MAX_DESC}).",
                 "Cut to the essentials; move detail into the body.")
    elif len(desc) < 40:
        s += add("WARN", "S5", "Structure", 2, 5, f"description is only {len(desc)} chars — too thin to route on.",
                 "Add the trigger context: what it does, on what input, when to pick it.")
    else:
        s += add("OK", "S5", "Structure", 5, 5, f"description length is healthy ({len(desc)} chars).")
    rep.dims["Structure"] = (s, 25)

    # ---------------- Triggerability (25)
    t = 0.0
    desc_l = desc.lower()
    has_action = any(w in desc_l for w in ACTION_WORDS)
    t += add("OK" if has_action else "WARN", "T1", "Triggerability", 5 if has_action else 2, 5,
             "description states an action." if has_action else "description has no clear action verb.",
             "" if has_action else "Lead with a verb: 'Generates…', 'Converts…', 'Audits…'.")

    has_trigger = any(p in desc_l for p in TRIGGER_PHRASES)
    t += add("OK" if has_trigger else "ERROR", "T2", "Triggerability", 5 if has_trigger else 0, 5,
             "description declares when to use it." if has_trigger
             else "description never says WHEN to use it — this is the #1 reason skills never fire.",
             "" if has_trigger else "Append: 'Use when the user asks to …'.")

    third = not bool(FIRST_PERSON.search(body)) and not desc_l.startswith(("i ", "you "))
    t += add("OK" if third else "WARN", "T3", "Triggerability", 5 if third else 2, 5,
             "written in third person (matches how the agent reads it)." if third
             else "contains first/second person ('I can', 'you should').",
             "" if third else "Rewrite in imperative/third person: 'Extract…', not 'I will extract…'.")

    has_trigger_section = bool(re.search(r"(?im)^#{1,4}\s*(when to use|triggers?|usage|适用|触发|何时使用)", body))
    t += add("OK" if has_trigger_section else "WARN", "T4", "Triggerability", 5 if has_trigger_section else 2, 5,
             "body has an explicit trigger section." if has_trigger_section
             else "no 'When to use' section in the body.",
             "" if has_trigger_section else "Add '## When to use' with 3-5 concrete user phrasings.")

    has_nouns = sum(1 for n in CONCRETE_NOUNS if n in desc_l) >= 2
    t += add("OK" if has_nouns else "WARN", "T5", "Triggerability", 5 if has_nouns else 2, 5,
             "description names concrete objects (files, formats, artifacts)." if has_nouns
             else "description is abstract — no concrete object named.",
             "" if has_nouns else "Name the artifacts: 'PDF invoices', 'git commits', 'screenshots'.")
    rep.dims["Triggerability"] = (t, 25)

    # ---------------- Executability (20)
    e = 0.0
    steps = len(re.findall(r"(?m)^\s*(?:\d+\.|[-*])\s+\S", body))
    e += add("OK" if steps >= 3 else "WARN", "E1", "Executability", 5 if steps >= 3 else 2, 5,
             f"{steps} procedural steps found." if steps >= 3 else f"only {steps} steps — the agent will improvise.",
             "" if steps >= 3 else "Write a numbered workflow the agent can follow.")

    # Paths in prose must exist; paths inside fenced blocks may be illustrative.
    prose = re.sub(r"```.*?```", "", body, flags=re.S)
    hard_refs = {r for r in PATH_REF.findall(prose) if "*" not in r}
    soft_refs = {r for r in PATH_REF.findall(body) if "*" not in r} - hard_refs
    missing_hard = sorted(r for r in hard_refs if not (skill_dir / r).exists())
    missing_soft = sorted(r for r in soft_refs if not (skill_dir / r).exists())
    if missing_hard:
        e += add("ERROR", "E2", "Executability", 0, 5,
                 f"referenced but missing: {', '.join(missing_hard)}",
                 "Create the file or fix the path — broken refs are silent failures.")
    elif not hard_refs and not soft_refs:
        e += add("WARN", "E2", "Executability", 2, 5, "no scripts/ or resources/ referenced.",
                 "If the skill touches files, ship a script and call it by relative path.")
    elif hard_refs:
        e += add("OK", "E2", "Executability", 5, 5, f"all {len(hard_refs)} referenced paths exist.")
    else:
        note = f" ({len(missing_soft)} illustrative path(s) in examples, not checked)" if missing_soft else ""
        e += add("OK", "E2", "Executability", 5, 5, f"script paths resolve{note}.")

    has_cmd = bool(re.search(r"```(?:bash|sh|shell|python|console)?\n", body))
    e += add("OK" if has_cmd else "WARN", "E3", "Executability", 5 if has_cmd else 2, 5,
             "includes a runnable command block." if has_cmd else "no command block.",
             "" if has_cmd else "Show the exact command, not a description of it.")

    if 40 <= rep.lines <= 500:
        e += add("OK", "E4", "Executability", 5, 5, f"body is {rep.lines} lines — within the sweet spot.")
    elif rep.lines < 40:
        e += add("WARN", "E4", "Executability", 2, 5, f"body is only {rep.lines} lines — probably under-specified.",
                 "Add the workflow, an example, and guardrails.")
    else:
        e += add("WARN", "E4", "Executability", 3, 5, f"body is {rep.lines} lines — burns context on every load.",
                 "Keep SKILL.md < 500 lines; push reference detail into resources/.")
    rep.dims["Executability"] = (e, 20)

    # ---------------- Reliability (15)
    r = 0.0
    has_examples = bool(re.search(r"(?im)^#{1,4}\s*(examples?|示例|例子)", body)) or (skill_dir / "examples").exists()
    concrete = False
    if has_examples:
        m = re.search(r"(?ims)^#{1,4}\s*(?:examples?|示例|例子)[^\n]*\n(.*?)(?=^#{1,4}\s|\Z)", body)
        seg = m.group(1) if m else body
        concrete = bool(re.search(r"[`/\d]", seg))
    if has_examples and concrete:
        r += add("OK", "R1", "Reliability", 5, 5, "has concrete examples (real paths or values).")
    elif has_examples:
        r += add("WARN", "R1", "Reliability", 3, 5,
                 "examples are generic placeholders — the agent has nothing concrete to imitate.",
                 "Replace 'a typical file' with a real path and a real output line.")
    else:
        r += add("WARN", "R1", "Reliability", 2, 5, "no examples — the agent has no gold standard to imitate.",
                 "Add one input→output example.")

    has_guard = any(w in low_body for w in GUARDRAIL_WORDS)
    r += add("OK" if has_guard else "WARN", "R2", "Reliability", 5 if has_guard else 2, 5,
             "states guardrails / failure boundaries." if has_guard else "no guardrails — risky skills get uninstalled.",
             "" if has_guard else "Add '## Guardrails': what it must never do, when to stop and ask.")

    has_output = any(w in low_body for w in OUTPUT_WORDS)
    r += add("OK" if has_output else "WARN", "R3", "Reliability", 5 if has_output else 2, 5,
             "defines the output contract." if has_output else "no output contract — results will be inconsistent.",
             "" if has_output else "State exactly what the user gets back: format, fields, file path.")
    rep.dims["Reliability"] = (r, 15)

    # ---------------- Discoverability (15)
    d = 0.0
    has_readme = (skill_dir / "README.md").exists()
    d += add("OK" if has_readme else "WARN", "D1", "Discoverability", 5 if has_readme else 0, 5,
             "README present." if has_readme else "no README — nobody finds or installs it.",
             "" if has_readme else "Add README.md: one-line pitch, install, example.")

    has_license = any((skill_dir / f).exists() for f in ("LICENSE", "LICENSE.md", "LICENSE.txt"))
    d += add("OK" if has_license else "WARN", "D2", "Discoverability", 5 if has_license else 0, 5,
             "LICENSE present." if has_license else "no LICENSE — companies can't adopt it.",
             "" if has_license else "Add MIT or Apache-2.0.")

    install_hint = False
    if has_readme:
        rd = (skill_dir / "README.md").read_text(encoding="utf-8", errors="replace").lower()
        install_hint = any(k in rd for k in ("install", "git clone", "npx", "cp -r", "安装"))
    d += add("OK" if install_hint else "WARN", "D3", "Discoverability", 5 if install_hint else 0, 5,
             "README shows install commands." if install_hint else "no install instructions found in README.",
             "" if install_hint else "Give a copy-paste install line — the single biggest star factor.")
    rep.dims["Discoverability"] = (d, 15)

    total = sum(v[0] for v in rep.dims.values())
    rep.score = int(round(total))
    rep.grade = "A" if rep.score >= 90 else "B" if rep.score >= 75 else "C" if rep.score >= 60 else "D"
    return rep


# ---------------------------------------------------------------- rendering

BAR = {"Structure": "Structure", "Triggerability": "Trigger",
       "Executability": "Execute", "Reliability": "Reliab.",
       "Discoverability": "Discover"}


def render(rep: Report) -> str:
    out = []
    out.append(f"skill-lint  ·  {rep.path}")
    out.append(f"score {rep.score}/100   grade {rep.grade}")
    out.append("")
    for dim, (got, mx) in rep.dims.items():
        filled = int(round(got / mx * 10)) if mx else 0
        out.append(f"  {BAR.get(dim, dim):<9} {got:>4.0f}/{mx:<3} {'#' * filled}{'.' * (10 - filled)}")
    out.append("")
    order = {"ERROR": 0, "WARN": 1, "OK": 2}
    for f in sorted(rep.findings, key=lambda x: (order[x.level], x.dim)):
        if f.level == "OK":
            continue
        tag = "[!]" if f.level == "ERROR" else "[~]"
        out.append(f"{tag} {f.code:<3} {f.message}")
        if f.fix:
            out.append(f"       fix: {f.fix}")
    errors = sum(1 for f in rep.findings if f.level == "ERROR")
    warns = sum(1 for f in rep.findings if f.level == "WARN")
    oks = sum(1 for f in rep.findings if f.level == "OK")
    out.append("")
    out.append(f"{oks} passed · {warns} warnings · {errors} errors")
    if errors == 0 and rep.score >= 85:
        out.append("ship it.")
    elif errors:
        out.append("blocked: fix errors before publishing.")
    else:
        out.append("usable, but the warnings are what separate a 30-star skill from a 3k-star one.")
    return "\n".join(out)


# ---------------------------------------------------------------- scaffold

TEMPLATE = """---
name: {name}
description: {description}
---

# {title}

## When to use

- Use when the user asks to {requirement}.
- Use when the input arrives as a file, path, or pasted block of text.

## Workflow

1. **Inspect** — read the input and state in one line what you found.
2. **Decide** — pick the path; if it is ambiguous, ask exactly one question.
3. **Plan** — run the bundled script in preview mode:

   ```bash
   python scripts/{slug}_run.py --input <path> --dry-run
   ```

4. **Apply** — rerun without `--dry-run` once the plan looks right.
5. **Verify** — check the result against the criteria below.
6. **Report** — return the result in the contract below.

## Output

Return: what was produced, where it was written, and what the user should do next.

## Guardrails

- Do not modify files outside the working directory.
- Preview first; never overwrite without confirming.
- If the input is missing or unreadable, stop and ask — never guess.

## Examples

**Input:** a typical file for this task.
**Output:** a one-line summary plus the path of whatever was written.

## Verification

```bash
python scripts/skilllint.py score .
```

Keep the score at 85 or above before publishing.
"""

PLACEHOLDER_SCRIPT = '''#!/usr/bin/env python3
"""TODO: one line describing what this does."""

from __future__ import annotations

import argparse
import sys


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="TODO")
    ap.add_argument("--input", required=True, help="path to the input file")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, change nothing")
    args = ap.parse_args(argv)

    print(f"{'would process' if args.dry_run else 'processing'}: {args.input}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

MIT_LICENSE = """MIT License

Copyright (c) 2026 {author}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
"""


def scaffold(target: Path, requirement: str) -> int:
    words = [w for w in re.split(r"[^a-zA-Z0-9]+", requirement.lower()) if w]
    slug = "-".join(words)[:48].strip("-") or "new-skill"
    target = target / slug if target.name != slug else target
    target.mkdir(parents=True, exist_ok=True)
    (target / "scripts").mkdir(exist_ok=True)
    short = requirement.strip().rstrip(".")
    desc = (f"{short[:1].upper()}{short[1:]} — takes the matching input and returns the finished result. "
            "Use when the user asks for this task or hands over the matching input.")
    (target / "SKILL.md").write_text(
        TEMPLATE.format(name=slug, description=desc,
                        title=slug.replace("-", " ").title(),
                        slug=slug.replace("-", "_"), requirement=short.lower()),
        encoding="utf-8")
    script = target / "scripts" / f"{slug.replace('-', '_')}_run.py"
    script.write_text(PLACEHOLDER_SCRIPT, encoding="utf-8")
    script.chmod(0o755)
    (target / "LICENSE").write_text(MIT_LICENSE.format(author="skill author"), encoding="utf-8")
    (target / "README.md").write_text(
        f"# {slug}\n\n{short}.\n\n## Install\n\n"
        f"```bash\ngit clone <repo> && cp -r {slug} ~/.claude/skills/\n```\n\n## Usage\n\n"
        f"Ask your agent: \"{short}\"\n", encoding="utf-8")
    print(f"scaffolded {target}")
    print(f"next: python scripts/skilllint.py score {target}")
    return 0


# ---------------------------------------------------------------- cli

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="skilllint", description="Lint and score an Agent Skill.")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("score", help="score a skill directory")
    ps.add_argument("path")
    ps.add_argument("--json", action="store_true")
    ps.add_argument("--min-score", type=int, default=0)

    pn = sub.add_parser("new", help="scaffold a new skill")
    pn.add_argument("requirement")
    pn.add_argument("--dir", default=".")

    args = p.parse_args(argv)

    if args.cmd == "new":
        return scaffold(Path(args.dir), args.requirement)

    path = Path(args.path)
    if not path.exists():
        print(f"skilllint: no such path: {path}", file=sys.stderr)
        return 2

    rep = check(path)
    if args.json:
        print(json.dumps(rep.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(render(rep))

    errors = sum(1 for f in rep.findings if f.level == "ERROR")
    if errors or rep.score < args.min_score:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
