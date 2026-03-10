# Open Deep Research

Open Deep Research is a small, practical repo for building a scholarly "deep research" workflow on top of [OpenAlex](https://docs.openalex.org/api-entities/works) and an OpenAI-compatible LLM.

It does four things:
- plans search queries from a research question
- searches and expands papers through OpenAlex references and citations
- fetches open-access text when available
- writes a Markdown literature review with explicit paper citations

The project is intentionally simple enough to teach in an Information Retrieval course and strong enough to serve as a working baseline for assignments.

## Why this stack

- **OpenAlex** is the discovery graph and metadata backbone.
- **OpenAI-compatible chat models** handle planning, reranking, and synthesis.
- **Local scoring and trace logging** keep the retrieval decisions inspectable.

## Repository layout

```text
open_deep_research/
  src/open_deep_research/
    api.py
    cli.py
    config.py
    fetchers.py
    llm.py
    models.py
    openalex.py
    planner.py
    reporting.py
    research.py
  tests/
  .env.example
  pyproject.toml
```

## Quickstart

1. Create a virtual environment.
2. Install the package.
3. Set your API keys.
4. Run a research job.

```bash
cd /Users/birger/Documents/uppsala_lektorat/Information_Retrieval_Course/open_deep_research
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
open-deep-research research "How do retrieval-augmented generation systems reduce hallucinations?" --output-dir outputs/rag
```

If you also want PDF extraction support:

```bash
pip install -e '.[pdf]'
```

Install directly from GitHub without cloning:

```bash
pip install "open-deep-research @ git+https://github.com/BirgerMoell/open-deep-research.git"
```

## Environment variables

- `OPENALEX_MAILTO`: recommended for OpenAlex polite-pool access
- `OPENALEX_API_KEY`: optional OpenAlex premium key
- `OPENAI_BASE_URL`: defaults to `https://api.openai.com/v1`
- `OPENAI_API_KEY`: required for hosted OpenAI, often omitted for local OpenAI-compatible servers
- `OPENAI_MODEL`: defaults to `gpt-4o-mini`

## Commands

Research and write a report:

```bash
open-deep-research research "What are the main evaluation methods for neural information retrieval?" --final-papers 8
```

Read the question from stdin and print only the report body, which is the most convenient mode for agent skills:

```bash
printf '%s' "How are citation graphs used in scientific literature retrieval?" | \
  open-deep-research research --stdin --format report
```

Disable the LLM and run the retrieval-only pipeline:

```bash
open-deep-research research "What are the main evaluation methods for neural information retrieval?" --no-llm
```

Inspect the query plan only:

```bash
open-deep-research plan "How do agentic retrieval systems differ from standard RAG?"
```

Print only the planned queries:

```bash
open-deep-research plan "How do agentic retrieval systems differ from standard RAG?" --format queries
```

Run the local JSON API:

```bash
open-deep-research serve --host 127.0.0.1 --port 8080
```

Example request:

```bash
curl -X POST http://127.0.0.1:8080/research \
  -H 'Content-Type: application/json' \
  -d '{"question": "What are the main design patterns in deep research systems?", "final_papers": 6}'
```

## Outputs

Each run writes:
- `report.md`: literature review in Markdown
- `papers.json`: normalized paper metadata and scores
- `trace.json`: planned queries, expansion edges, and selection decisions

`research` also supports skill-friendly stdout modes:
- `--format json`: full structured result
- `--format paths`: just the output file locations
- `--format report`: print `report.md`
- `--format papers`: print `papers.json`
- `--format trace`: print `trace.json`

## Deep research workflow

```text
question
  -> query plan
  -> OpenAlex search
  -> reference/citation expansion
  -> heuristic scoring
  -> optional LLM reranking
  -> OA text fetch
  -> report synthesis
```

## Notes

- This repo is designed for open scholarly discovery, not closed publisher access.
- OpenAlex does not contain all full texts. The pipeline therefore falls back to abstracts when open text cannot be fetched.
- For large-scale ingestion, OpenAlex also provides snapshots and an official CLI: [OpenAlex CLI](https://docs.openalex.org/download-all-data/openalex-cli).

## Codex skill use

This repo now includes a minimal skill template at [codex_skill/open-deep-research/SKILL.md](codex_skill/open-deep-research/SKILL.md).

That template assumes the CLI is installed and then uses stdin plus explicit output modes, which is the cleanest way for an agent to call the tool:

```bash
printf '%s' "$QUESTION" | open-deep-research research --stdin --format report
```

## Official references

- [OpenAlex Works docs](https://docs.openalex.org/api-entities/works)
- [OpenAlex Work object docs](https://docs.openalex.org/api-entities/works/work-object)
- [OpenAlex rate limits](https://docs.openalex.org/how-to-use-the-api/rate-limits-and-authentication)
- [OpenAI Chat Completions](https://platform.openai.com/docs/api-reference/chat/create)
- [Responses vs Chat Completions](https://platform.openai.com/docs/guides/responses-vs-chat-completions)
