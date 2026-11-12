# Code Security Reviewer

Review small source files for potential security, performance, and maintainability issues. The API and Streamlit dashboard run local checks without a model key. With an OpenAI key, the reviewer can also generate explanations and propose changes for a developer to review.

## How a review works

1. The dashboard or an HTTP client sends source and its language to `POST /review`.
2. The orchestrator runs a code analyzer, pattern-based security and performance checks, and quality checks. The coordinator aggregates findings and calculates heuristic scores.
3. With a model configured, the rewrite agent requests a complete replacement for individual findings. The API discards malformed or truncated responses, unchanged source, and Python proposals that fail to compile. Python comparisons ignore formatting and comment changes. The server displays proposals as source text and never executes or applies them.
4. PostgreSQL stores the submitted source, review metadata, and summary. The response also includes individual findings and any generated proposals. Findings and proposals are currently available only in that response.

## Run locally

Use Python 3.12 and a PostgreSQL database dedicated to this demo. Start in the project directory.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
```

Provision an empty database and a database role that can create tables there. Set `DATABASE_URL` in the API process environment to its PostgreSQL connection URL. Store real credentials outside version control. The API creates the tables at startup.

```sh
export DATABASE_URL='postgresql://reviewer:replace-me@127.0.0.1:5432/code_reviewer'
unset OPENAI_API_KEY
python -m uvicorn api.server:app --host 127.0.0.1 --port 8000
```

In a second terminal, activate the same virtual environment from the project directory and run the dashboard.

```sh
source .venv/bin/activate
python -m streamlit run dashboard/app.py --server.address 127.0.0.1
```

Open the dashboard at `http://127.0.0.1:8501` and use `http://127.0.0.1:8000` as its API URL. Interactive API documentation is at `http://127.0.0.1:8000/docs`.

Set `OPENAI_API_KEY` in the API process environment and restart it to enable optional model assistance. `LLM_MODEL` overrides the configured default, `gpt-4o-mini`. When model assistance is enabled, review and proposal prompts may send submitted source, including the complete source for each proposed replacement, to OpenAI. Use synthetic examples or code you are authorized to share with the provider. The local database retains submitted source in both modes.

## Try the offline example

With the API running and its model key unset, submit the bundled Python SQL-injection fixture.

```sh
curl --fail --silent --show-error http://127.0.0.1:8000/health
python - <<'PY' | curl --fail --silent --show-error \
  -H 'Content-Type: application/json' --data-binary @- \
  http://127.0.0.1:8000/review
import json
from pathlib import Path

code = Path("data/test_cases/python/insecure/sql_injection.py").read_text()
print(json.dumps({"code": code, "language": "python"}))
PY
```

The review returns `status: completed`, a review ID, a `sql_injection` finding under `security.findings`, and an empty `rewrites` list. The same fixture is available in the dashboard's Test Cases tab.

## Test

```sh
python -m unittest discover -s tests -v
```

The proposal tests use deterministic completion fixtures. To include the API and persistence checks, supply `TEST_DATABASE_URL` for disposable PostgreSQL. The test role must be able to create and drop its own schema. The database tests create a uniquely named schema per test and remove it afterward.

```sh
TEST_DATABASE_URL='postgresql://reviewer:replace-me@127.0.0.1:5432/code_reviewer_test' \
  python -m unittest discover -s tests -v
```

## Limits

- All proposals use `rewrite_mode: review` with a null `confidence_score`. `validation_status: syntax_checked` means the replacement compiled as Python. A proposal may still change behavior, miss the reported issue, omit unrelated code, or introduce a new vulnerability. The dashboard shows the original and proposed source side by side.
- For other languages, proposals carry `validation_status: unchecked`. Python and SQL have bundled examples. Other languages use generic heuristics.
- Static findings and scores are heuristic. Use project-specific tests and security checks before adopting a change. Long files may exceed model output limits and yield no proposal.
- The API has no authentication, and review history is not exposed. Keep the demo on loopback and use a dedicated database with an appropriate retention policy. Avoid pasting secrets.
- Live model quality and cost were not evaluated as part of the offline test suite.

See [Python's AST documentation](https://docs.python.org/3.12/library/ast.html#ast.parse) and [OWASP's guidance on model output handling](https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/).

## License

[MIT](LICENSE.txt)

