# Skills Graph Builder

Explore a synthetic skills catalog, ingest evidence for a person, compare their skills with a role, and generate a learning plan. FastAPI serves the catalog and workflow. Streamlit displays the results.

## Run locally

Use Python 3.12. From this project directory, create an environment and start the API.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn src.app:app --host 127.0.0.1 --port 8000
```

Run the UI in a second terminal with the same environment active.

```bash
python -m streamlit run ui/streamlit_app.py --server.address 127.0.0.1
```

Open [the UI](http://127.0.0.1:8501) or [the API explorer](http://127.0.0.1:8000/docs). The API loads role requirements and bundled sample profile metadata from disk. Startup and catalog browsing work without a provider key.

## Try the workflow

Check the running API and inspect a sample person's current skills without calling the provider.

```bash
curl --fail-with-body http://127.0.0.1:8000/health
curl --fail-with-body http://127.0.0.1:8000/person/p100/skills
```

The expected responses on a fresh start are `{"status":"ok"}` and `[]`. To try live analysis, copy `.env.example` to `.env`, set `OPENAI_API_KEY`, and restart the API. Use only synthetic evidence for this example. Ingestion and ranking send data to OpenAI and may incur charges.

```bash
python scripts/load_seed_data.py p100
curl --fail-with-body 'http://127.0.0.1:8000/roles/matches?person_id=p100&top_k=3'
curl --fail-with-body 'http://127.0.0.1:8000/recommendations/p100?role_id=r_data_analyst'
```

## How it works

- Explicit profile ingestion extracts skills from evidence, maps them to the local ontology, and stores the profile, skills, and evidence vectors in memory.
- Role matching embeds the person's skill labels and the role requirements. It compares the normalized mean vectors with cosine similarity. An unprocessed profile has no matches. Provider failures return a clear error.
- Gap plans compare skill labels and list courses from the local CSV. An explicitly selected role can be used without an embedding call. Missing skills are ordered by must-have status and weight.

## Configuration and tests

Keep `OPENAI_API_KEY` in the environment or ignored `.env`. Override the default `gpt-4o-mini` and `text-embedding-3-small` models through `LLM_MODEL` and `EMBEDDING_MODEL`. Restart and reingest profiles after changing the embedding model. For optional plan event tracking, install `mlflow-skinny==3.18.0` and set `MLFLOW_TRACKING_URI` to a trusted tracking server. Tracking is off by default.

```bash
python -m unittest discover -s tests -v
```

The suite uses deterministic provider fixtures and makes no paid calls. See [API.md](API.md) for the request and response contracts.

## Limits

Profiles, skills, and vectors are in memory and reset when the API restarts. Rank scores use unweighted mean vectors. Role weights and must-have flags affect gap ordering. Scores are prototype recommendations for human review. The demo has no user authentication or access controls. Use synthetic data locally and review data handling before using employee evidence or enabling external tracking.
