# Open Deep Research Commands

## Install or upgrade

```bash
pip install -U open-deep-research-cli
```

## Direct report to stdout

```bash
printf '%s' "$QUESTION" | python3 -m open_deep_research.cli research --stdin --format report
```

## Return only output paths

```bash
printf '%s' "$QUESTION" | python3 -m open_deep_research.cli research --stdin --format paths
```

## Retrieval-only baseline

```bash
printf '%s' "$QUESTION" | python3 -m open_deep_research.cli research --stdin --no-llm --format report
```

## Plan only

```bash
printf '%s' "$QUESTION" | python3 -m open_deep_research.cli plan --stdin --format json
```

## Output files

- `report.md`: user-facing synthesis
- `papers.json`: selected papers, metadata, scores
- `trace.json`: search queries and expansion trace
