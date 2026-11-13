# Sales and Customer Success QBR Builder

Generate a quarterly business review draft from synthetic CRM, product usage, and support data. The pack includes an executive summary, account health score, insights, metrics, and suggested actions. A reviewer can approve, reject, or request changes.

## How a pack is built

1. `POST /qbr/generate` saves a linked request and draft pack, then starts a background task in the API process.
2. The orchestrator plans, fetches the three source snapshots, aggregates them, generates insights, and finalizes the draft. LangGraph runs this sequence once per request. The same source snapshots feed the report and are saved with it. A sequential fallback uses the same stages if LangGraph is absent.
3. The API stores step events as the run proceeds. On success it saves the outputs and moves the pack to `pending_approval`. If generation or storage fails, the pack and run are marked `failed`. Fetch the pack and its trace through separate endpoints.
4. The Streamlit dashboard submits jobs, displays packs, and records review decisions. The API accepts a decision only while the pack is pending approval.

## Run locally

Use Python 3.12. From this project directory, create an isolated environment and install the requirements.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
```

The API creates a SQLite database named `qbr_builder.sqlite` in the project directory by default. To use a different database, set `DATABASE_URL` in the API process environment. A PostgreSQL URL such as `postgresql://reviewer:replace-me@127.0.0.1:5432/qbr_demo` uses psycopg. Use a dedicated database and give the database role permission to create tables. Keep credentials outside version control.

For a local run without provider calls, leave the model key unset.

```sh
unset OPENAI_API_KEY
python -m uvicorn api.server:app --host 127.0.0.1 --port 8001
```

In a second terminal, activate the environment from the same project directory and start the dashboard.

```sh
source .venv/bin/activate
python -m streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8501
```

Open the dashboard at `http://127.0.0.1:8501` or the API reference at `http://127.0.0.1:8001/docs`. The dashboard uses that API by default. Set `API_BASE_URL` in the dashboard environment or Streamlit secrets to override it.

To try model-assisted insight generation, set `OPENAI_API_KEY` in the API process and restart it. `LLM_MODEL` defaults to `gpt-4o-mini`. This mode sends the account name, goals, period, and synthetic source data to OpenAI. Use demo inputs. With the key unset, the API uses deterministic rules. A provider or response-validation failure also falls back to those rules, with `has_error: true` in the generation checkpoint.

## Try the offline example

Submit the mixed account scenario. The response contains a `pack_id` and status `processing`.

```sh
curl --fail --silent --show-error http://127.0.0.1:8001/qbr/generate \
  -H 'Content-Type: application/json' \
  --data '{"account_id":"acc-mixed-001","account_name":"Acme Demo","quarter":"Q1-2025","period_start":"2025-01-01","period_end":"2025-03-31","goals":["Renewal","Product Adoption"]}'
```

Substitute the returned pack ID below. Wait until the pack reaches `pending_approval` before reviewing it.

```sh
pack_id='replace-with-pack-id'
curl --fail --silent --show-error "http://127.0.0.1:8001/qbr/$pack_id"
curl --fail --silent --show-error "http://127.0.0.1:8001/qbr/$pack_id/events"
```

A completed trace has one start and one completion for each of the five stages, plus source and generation checkpoints. In the dashboard, `acc-win-001`, `acc-risk-001`, and `acc-mixed-001` select different demo scenarios.

## Test

```sh
python -m unittest discover -s tests -v
```

The tests use deterministic fixtures, a temporary SQLite database, and no live provider. They check one execution per stage, snapshot consistency, trace order, persistence, and failure handling.

## Current limits

- The source adapters return synthetic data. The account ID selects a scenario, and sample values and dates are fixed. The demo has no live MCP, CRM, product analytics, or support connections.
- Health scores are illustrative. Review all claims, metrics, and actions before sharing a pack.
- Background work runs in the API process. A restart can interrupt it. Submitting again creates a new pack. Requesting changes records a review decision, and automatic regeneration from feedback and version history are roadmap items. Deck export is also planned.
- This is a local demo with no authentication. Keep the API and dashboard on loopback. Treat stored pack data and traces as sensitive if you extend the demo to real sources.
- The trace records stage status and counts. It omits model reasoning and the source data is stored separately.

## License

[MIT](LICENSE.txt)
