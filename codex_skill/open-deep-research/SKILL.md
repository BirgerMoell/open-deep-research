---
name: open-deep-research
description: Use this skill when the user wants scholarly deep research, literature reviews, citation-graph exploration, or OpenAlex-based source discovery. It uses the open-deep-research CLI to plan searches, expand through citations and references, and generate structured outputs or a Markdown report.
---

# Open Deep Research

Use this skill for research questions over scholarly papers when broad source discovery matters more than a local RAG corpus.

## Preconditions

- The `open-deep-research` CLI must be installed from this repo.
- The local environment should define `OPENALEX_API_KEY` and optionally `OPENAI_API_KEY`.

## Core workflow

1. Plan the search if the query is broad or ambiguous:

```bash
open-deep-research plan --stdin --format json
```

2. Run deep research and print the final Markdown report:

```bash
open-deep-research research --stdin --format report
```

3. If you need inspectable artifacts for follow-up steps, print only paths:

```bash
open-deep-research research --stdin --format paths
```

Then read:
- `report.md` for the literature review
- `papers.json` for selected papers and scores
- `trace.json` for search and expansion decisions

## Usage guidance

- Prefer `--format report` when the user wants a directly readable answer.
- Prefer `--format paths` when you expect to inspect trace files afterward.
- Use `--no-llm` only when no LLM is configured or when you want a retrieval-only baseline.
- For long questions, pass them through stdin instead of shell quoting.

## Limits

- OpenAlex is the discovery graph, not a source of all full texts.
- Closed-access publisher pages may not yield usable full text.
- Broad questions may still need manual refinement after the first pass.

