# Research Report Writer

The API turns a research question into a report with numbered references. It can run a reproducible offline example or use Tavily search results and an OpenAI model for live analysis. The Streamlit dashboard submits requests and retrieves stored reports.

## Run locally

Use Python 3.12 and a dedicated PostgreSQL database. From this project directory, create an environment and copy the configuration template.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Set `DATABASE_URL` in the ignored `.env` file to your development database. The database must already exist. Startup creates tables that are missing. The template selects `fixture` mode so you can try the workflow without provider credentials.

```bash
python -m uvicorn api.server:app --host 127.0.0.1 --port 8000
```

In a second terminal, activate the same environment and run `python -m streamlit run dashboard/app.py --server.address 127.0.0.1`. Open [the API explorer](http://127.0.0.1:8000/docs) or [the dashboard](http://127.0.0.1:8501). Set `RESEARCH_API_URL` in the dashboard's environment if your API uses another address.

## Generate and retrieve a report

```bash
curl --fail-with-body http://127.0.0.1:8000/research \
  -H 'Content-Type: application/json' \
  -d '{"research_query":"How does a solar panel behave over a day?","max_sources":2}'
```

In fixture mode the response identifies `search_mode` as `fixture`, includes a labeled report, and cites fixed synthetic examples at `.invalid` URLs. The examples demonstrate the data flow for any valid query. Copy the returned `request_id` into `GET /research/{request_id}` or the dashboard to retrieve the report and its source catalog.

## Live research and source provenance

To enable live research, set `RESEARCH_SEARCH_MODE=tavily`, `TAVILY_API_KEY`, and `OPENAI_API_KEY` in the server environment or `.env`. The model defaults to `gpt-4o-mini` and can be set with `LLM_MODEL`. Restart the API after editing the configuration. Live searches and model calls can incur charges and send the research query or selected excerpts to the configured providers.

1. Tavily returns up to 20 results. The server validates URLs, deduplicates results, and uses the excerpts returned by Tavily.
2. Source screening applies a simple domain heuristic. The default cutoff is `0.5`. Analysis and synthesis receive the selected excerpts, and the renderer builds numbered references from their source records.
3. A successful request saves the report, findings, source metadata, and mode to PostgreSQL. Missing credentials or unavailable providers return HTTP 503. An empty search or a cutoff that excludes all sources returns HTTP 422.

A reference links to the original URL. The service uses search excerpts and does not fetch source pages itself. The screening score is a heuristic. Citation IDs link report sections to selected evidence, but they do not verify individual model claims. Check the original sources before relying on a report.

## Tests

```bash
python -m unittest discover -s tests -v
```

The search tests use deterministic responses. To include API and persistence tests, set `TEST_DATABASE_URL` to a disposable PostgreSQL database and rerun the same command. Those tests create and drop an isolated schema. Fixture and simulated live tests require no provider credentials.

See [LICENSE.txt](LICENSE.txt) for the license.
