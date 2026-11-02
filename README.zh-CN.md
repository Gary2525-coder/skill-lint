# skill-lint

**写 Agent Skill 的正确姿势：先让它能被触发，再谈好不好用。**

大多数 skill 从来没被加载过。不是写得差，是模型根本不知道该在什么时候用它。
`skill-lint` 给你两样东西：

1. 一个 skill：把一句话需求变成完整、可直接发布的 skill 目录。
2. 一个 CLI：给任意 skill 打分，专治那个让 90% 的 skill 悄悄失效的 `description` 问题。

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
[~] R1  no examples — the agent has no gold standard to imitate.

11 passed · 8 warnings · 1 errors
blocked: fix errors before publishing.
```

改完再跑一遍，通过就发。整个循环就这么多。

## 安装

```bash
git clone https://github.com/<your-name>/skill-lint.git
mkdir -p ~/.claude/skills && cp -r skill-lint ~/.claude/skills/
```

兼容任何读取 `SKILL.md` 约定的客户端：Claude Code、Codex、Cursor。
零依赖、零配置、不需要 API Key。

## 使用

对你的 Agent 说：

> 帮我写一个把 PDF 发票转成 CSV 台账的 skill。

它会先收敛需求，判断该做成纯指令还是加脚本，然后写 `SKILL.md`、生成脚本、自动打分，最后告诉你分数和下一步最该改哪里。

也可以直接用命令行：

```bash
python scripts/skilllint.py new "convert pdf invoices to csv"   # 生成骨架
python scripts/skilllint.py score ./pdf-invoices-to-csv         # 打分
python scripts/skilllint.py score ./pdf-invoices-to-csv --json  # 机器可读
python scripts/skilllint.py score ./my-skill --min-score 85     # CI 卡口，失败退出码 1
```

## 五个评分维度

| 维度 | 分值 | 它到底在问什么 |
|---|---|---|
| **Structure** 结构 | 25 | front matter 合规吗？`name` 和目录名一致吗？`description` 长度对吗？ |
| **Triggerability** 可触发性 | 25 | 描述里有没有动作 + 明确的“何时使用”？正文有没有触发段？ |
| **Executability** 可执行性 | 20 | 有编号步骤吗？引用的文件真的存在吗？有能跑的命令吗？ |
| **Reliability** 可靠性 | 15 | 有具体示例、有边界约束、有输出契约吗？ |
| **Discoverability** 可发现性 | 15 | README、LICENSE、一行能复制的安装命令？ |

等级：**A** ≥ 90 · **B** ≥ 75 · **C** ≥ 60 · **D** < 60。
低于 75 就别发了——你是在让陌生人免费帮你调 prompt。

## 它抓的那个坑

```yaml
# 可触发性得 0 分
description: A powerful skill for productivity workflows.

# 满分——动作 + 触发条件 + 具体产物
description: Converts PDF invoices into a CSV ledger with date, vendor, and total columns. Use when the user asks to extract, tabulate, or reconcile invoice data from PDFs.
```

第二条模型能匹配到，第一条永远匹配不到，正文写得再好也没用。
这是整个 skill 生态里投入产出比最高的一次修改，而几乎没人做。

## 免安装检查

```bash
curl -sO https://raw.githubusercontent.com/<your-name>/skill-lint/main/scripts/skilllint.py
python skilllint.py score ./my-skill
```

## CI 卡口

```yaml
- uses: actions/checkout@v4
- run: python scripts/skilllint.py score ./my-skill --min-score 85
```

以后谁把 description 改坏了，构建直接失败，而不是悄悄让 skill 失效。

## 另一半：给人看的那一半

CLI 只测机器那一半——路由、结构、契约。另一半是人在 GitHub 上滑过时，四秒内信不信你：
一行说清价值、贴一段真实的终端输出、一个能复制的安装块、MIT 协议。
`skill-lint` 只测最后两项，前两项得你自己写。

## 协议

MIT
*（内容由AI生成，仅供参考）*
