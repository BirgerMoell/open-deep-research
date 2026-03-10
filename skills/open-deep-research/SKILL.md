---
name: open-deep-research
description: Use this skill when the user wants a scholarly or clinical literature review, evidence scan, citation-graph exploration, or OpenAlex-based source discovery across many papers. It installs and uses the `open-deep-research` CLI from PyPI, runs deep research through OpenAlex, expands through references and citations, and returns a Markdown report plus inspectable trace files.
---

# Open Deep Research

Run broad literature discovery when a local corpus is not enough.

## Workflow

1. Ensure the CLI is installed or upgraded:

```bash
bash <skill-directory>/scripts/install_or_upgrade.sh
```

2. Choose the output mode:
- Use `--format report` when the user wants a readable answer immediately.
- Use `--format paths` when you expect to inspect `report.md`, `papers.json`, or `trace.json` afterward.
- Use `--no-llm` only when no LLM provider is configured or when you want a retrieval-only baseline.

3. Run the research job with stdin, not shell quoting:

```bash
printf '%s' "$QUESTION" | bash <skill-directory>/scripts/run_report.sh
```

For inspectable artifact paths:

```bash
printf '%s' "$QUESTION" | bash <skill-directory>/scripts/run_paths.sh
```

## Defaults

- Prefer OpenAlex-backed discovery for paper finding and citation expansion.
- Prefer the PyPI package `open-deep-research-cli` rather than editing the repo in place.
- Prefer `report.md` for direct user-facing synthesis.
- Prefer reading `trace.json` when you need to justify why papers were selected.

## Clinical Use

- Use this skill for evidence gathering, not for autonomous clinical decisions.
- When the user asks a medical question, present the result as a literature scan or evidence summary, not as personal medical advice.
- State clearly when the output is based on abstracts or partial open-access text rather than full articles.

## Outputs

The CLI writes:
- `report.md`
- `papers.json`
- `trace.json`

Read [references/commands.md](references/commands.md) when you need exact command variants or output behavior.
