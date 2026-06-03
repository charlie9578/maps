# academic-citations-map

Interactive **citation network** around a scholarly work, built from [OpenAlex](https://openalex.org/). Pick a seed paper (search or work id), then expand **references** (outgoing) and **works that cite it** (incoming) up to a chosen depth. Directed edges mean **A cites B** (A → B).

## Run (from repo root)

```bash
uv pip install -r maps/academic-citations-map/requirements.txt
python maps/academic-citations-map/main.py --search "Penmanshiel wind farm data" --depth 1
```

Open `maps/academic-citations-map/output/citation_network.html` in a browser.

### CLI options

| Flag | Description |
|------|-------------|
| `--search QUERY` | OpenAlex full-text search to choose the seed paper |
| `--work-id W…` | Skip search; use a known OpenAlex work id |
| `--depth N` | `0` = seed + direct refs/citers only; `1` = one further hop (default for testing) |
| `--pick N` | When search returns several hits, pick by index (`--list-search` to list) |
| `--max-per-direction N` | Cap refs or citers per work per hop (default 30; raise for fuller graphs) |
| `--no-trim` | Keep every fetched paper |
| `--trim-mode connections\|smart\|simple` | **connections** (default): after expansion, drop least-connected papers until ≤ `--max-works`. **smart** / **simple**: per-hop rules, then the same cap |
| `--max-works N` | Final graph size cap by connection count (default 100; use `0` to disable cap) |
| `--min-connections N` | Hop‑1 floor in smart mode; simple mode uses N every hop (default 2) |
| `--min-cited-trim N` | Smart mode: drop hop 2+ degree‑2 nodes with `cited_by_count` &lt; N unless high score (default 5) |
| `--no-dedupe` | Keep separate OpenAlex ids even when DOI or normalized title+year match |

Examples:

```bash
python maps/academic-citations-map/main.py --list-search --search "Penmanshiel wind farm data"
python maps/academic-citations-map/main.py --work-id W4393687471 --depth 0
```

## Dependencies

Repo `.venv` plus map `requirements.txt`: `requests`, `plotly`, `networkx`.

## API keys

OpenAlex allows anonymous requests with a **User-Agent**; for heavier use or higher limits, add a free key from [openalex.org/settings/api](https://openalex.org/settings/api) to repo-root `.env`:

```bash
OPENALEX_API_KEY=your-key-here
```

Loaded via `lib.env` (see `.env.example`). Document rate limits on the [OpenAlex pricing page](https://developers.openalex.org/api-reference/authentication) if you raise `--depth` or remove caps.

## Data sources

| Source | Use | Link | License / terms | Accessed |
|--------|-----|------|-----------------|----------|
| OpenAlex | Work metadata, citation links (`cites` / `cited_by` filters) | https://openalex.org/ | [OpenAlex terms](https://openalex.org/terms) | 2026-06-03 |

No local CSV cache; the script calls the API on each run.

## Outputs

`output/citation_network.html` (gitignored) — Plotly network diagram; seed node in red.

## Notebooks

`notebook.ipynb` — explore search and `expand_citation_network()` with the **Maps (.venv)** kernel from the repo root.

## Depth semantics

- **Depth 0:** seed + papers it cites + papers that cite it.
- **Depth 1:** also expand those neighbors one hop (refs + citers of each).
- **Depth 2+:** repeat; increase `--max-per-direction` or reduce depth if responses are slow or large.

**Duplicate detection** (default on): search results and network nodes are merged when they share the same **DOI** or the same **normalized title + publication year**. The canonical record prefers the seed, then the highest `cited_by_count`. Merges are printed after each run.

**Trimming** (default on) ends with a **connection cap**: the seed is kept, then every paper tied for the fewest links is removed together; the process repeats until at most **100** works remain (`--max-works`). Only incident edges in the built network count. Use `--trim-mode smart` for additional per-hop pruning before the cap, or `--no-trim` to skip all trimming.

## Shared library

```python
from lib.env import load_repo_env  # optional; data_processing loads .env when fetching
```

## Standalone repo

Copy this folder, `requirements.txt`, and any `lib/` imports you use (`lib.env`).
