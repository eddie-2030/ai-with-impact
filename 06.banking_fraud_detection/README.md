# Banking Fraud Detection

Explore how rules use a synthetic transaction and its account history to produce a risk score, review status, and an alert. This is a local demo for inspecting behavior and persistence.

## How a transaction is assessed

1. `POST /transactions` validates the amount, database field lengths, coordinates, and timestamp. An existing transaction ID returns 409. Use `GET /transactions/{transaction_id}` to retrieve the original.
2. The API loads committed history for the same account, up to the transaction's event time. It excludes the current transaction ID and future events. Distinct events at the same timestamp are included.
3. The orchestrator checks six patterns. The risk calculator combines pattern strength, amount, the stored account risk profile, a new-device signal, and off-hours activity. Cases scoring at least 70 receive an investigation and an alert. Optional model calls enrich explanations. The rules determine scores, statuses, and alerts.
4. PostgreSQL commits the transaction, risk assessment, and any alert together. A duplicate competing request cannot overwrite the first saved result. A failed assessment returns 500 and saves no new records.

ISO timestamps with offsets are converted to UTC. Naive timestamps are treated as UTC, including legacy database values. Missing timestamps default to the current UTC time. Time-of-day checks use UTC. Matcher windows use strict lower bounds for the 1-hour and 24-hour cutoffs, and investigation windows include their lower endpoints.

## Run locally

Use Python 3.12 and a dedicated PostgreSQL database. From this project directory run:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
```

Set `DATABASE_URL` to a PostgreSQL connection URL for a role that can create tables in its working schema. Keep credentials outside version control. The API creates missing tables on startup.

```sh
export DATABASE_URL='postgresql://reviewer:replace-me@127.0.0.1:5432/fraud_demo'
unset OPENAI_API_KEY
python -m uvicorn api.server:app --host 127.0.0.1 --port 8000
```

From a second terminal, activate the same environment and start the dashboard.

```sh
source .venv/bin/activate
python -m streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8501
```

Open `http://127.0.0.1:8501` and keep the default API address. API reference is at `http://127.0.0.1:8000/docs`.

The demo works without a model key. Setting `OPENAI_API_KEY` enables optional explanatory calls using `LLM_MODEL` (default `gpt-4o-mini`). Prompts can send the amount, merchant, location, type, patterns, scores, and aggregate activity to OpenAI. Use synthetic records. Database rows retain transaction details, the risk assessment, and any alert.

## Submit and retrieve a synthetic transaction

Run this example against an empty demo database. Amounts accept a JSON number or decimal string. Send a decimal string to preserve the submitted precision through JSON parsing. Amounts must be positive and fit PostgreSQL `NUMERIC(15,2)`. Latitude and longitude, when supplied, must be finite and within their geographic ranges.

```sh
curl --fail --silent --show-error http://127.0.0.1:8000/transactions \
  -H 'Content-Type: application/json' \
  --data '{"transaction_id":"demo-001","user_id":"demo-account","amount":"1500.00","merchant":"Demo Store","location":"Detroit","timestamp":"2025-01-20T14:30:00Z"}'
curl --fail --silent --show-error http://127.0.0.1:8000/transactions/demo-001
curl --fail --silent --show-error 'http://127.0.0.1:8000/alerts?status=open'
```

For a new account, this example returns 6.00, low risk, the demo status `approved`, and no alert. Reusing `demo-001` returns 409 without changing the original record. Send an explicit ID for submissions you may need to retry. With an omitted ID the server creates a new ID for each submission.

## Test

```sh
python -m pip install -r requirements-dev.txt
LC_ALL=C python -m pytest -q
```

Tests disable live model access and use ephemeral PostgreSQL via `pgserver`. Alternatively, set `TEST_DATABASE_URL` to a dedicated disposable PostgreSQL database whose role can create and drop schemas. Each integration test uses its own schema. A seeded six-pattern anomaly exercises the complete medium-alert path at 71.50.

## Policy limits

- The score is a weighted rule score. It has no calibrated probability interpretation. Pattern scores are averaged, so adding a weaker match can reduce the composite.
- The maximum reachable scores for valid transactions are **63.50** for low-risk accounts, **68.00** for medium-risk accounts, and **72.50** for high-risk accounts. Only high-risk accounts can reach the 70 alert cutoff. The 80 and 90 cutoffs for high and critical severity are unreachable under these rules. Weights and cutoffs were retained. Labels and alerts now evaluate the same score rounded to two decimals.
- PostgreSQL stores the latest account profile. Replay uses that profile and already committed events. Concurrent events can be assessed before either appears in the other's history. The rule engine compares numeric amounts across currencies without currency conversion.
- This local service has no authentication and does not authorize or block payments. The repository has no labeled holdout data. Synthetic tests verify rule behavior, persistence, and score boundaries. They cannot estimate precision, recall, or false alerts on real transactions.

For future evaluation, use a chronological holdout with adjudicated outcomes and account history available at each event time. Measure recall, precision, false-alert rate, and review volume before revising weights or cutoffs. The Federal Reserve's revised model-risk guidance provides a reference for documenting assumptions and evaluating outcomes. [SR 26-2, April 17, 2026](https://www.federalreserve.gov/supervisionreg/srletters/SR2602.htm)

## License

[MIT](LICENSE.txt)

