# Meeting Note Analyzer

Turn a meeting transcript into a summary, action items, decisions, topics, participant contribution counts, and follow-ups. Use the FastAPI service, a Streamlit form, or the batch command for JSON meeting records.

## How an analysis is saved

1. The API and batch runner validate the same input. A meeting ID identifies one transcript, title, participant list, and date.
2. An identical submission with a saved analysis returns that analysis, including the original child IDs and follow-ups. A changed submission under the same ID returns HTTP 409 or a failed batch entry. Use a new ID for revised source material.
3. For a new ID, the service sends a single prompt to the configured OpenAI model and validates all result sections before saving. Missing credentials or provider errors return 503. Refused, truncated, or invalid output returns 502.
4. PostgreSQL saves the meeting and all extracted details in one transaction. The database's unique meeting ID allows only one result to be saved for concurrent first submissions. Simultaneous first submissions can each call the provider. A later retry reuses the saved result.
5. `GET /meetings/{meeting_id}` returns saved results. It omits the original transcript and participant contribution counts.

## Run locally

Use Python 3.12 and a dedicated PostgreSQL database. From this project's directory, run:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
```

Set `DATABASE_URL` to the connection URL for a database role that can create tables in its working schema. Keep credentials out of Git and shell history. The service creates missing tables at startup, including the follow-ups table in existing databases.

```sh
export DATABASE_URL='postgresql://reviewer:replace-me@127.0.0.1:5432/meeting_analyzer'
python -m uvicorn api.server:app --host 127.0.0.1 --port 8000
```

The API starts and serves saved meetings without a model key. To analyze new meetings, set `OPENAI_API_KEY` in the API or batch process environment before starting it. `LLM_MODEL` defaults to `gpt-4o-mini`. Analysis sends the transcript, title, and participants to OpenAI. Use data you are authorized to process. PostgreSQL retains the transcript and the analysis.

For the dashboard, activate the same environment in a second terminal and run:

```sh
source .venv/bin/activate
python -m streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8501
```

Open `http://127.0.0.1:8501` and use the default API address, `http://127.0.0.1:8000`. API reference is at `http://127.0.0.1:8000/docs`.

## Submit a transcript

Use a fresh ID for this example. For new records, choose a URL-safe ID such as `roadmap-demo`. With a configured provider, a successful response contains the summary, extracted details, and follow-ups. With the key unset, the same request returns 503 and leaves the database unchanged.

```sh
curl -sS -i http://127.0.0.1:8000/analyze \
  -H 'Content-Type: application/json' \
  --data '{"meeting_id":"roadmap-demo","title":"Roadmap planning","date":"2026-11-02T10:00:00","participants":["Alice"],"transcript":"Alice: The roadmap is approved. I will publish it by Friday. Let us review delivery next week."}'
curl -sS -i http://127.0.0.1:8000/meetings/roadmap-demo
```

The second request returns the saved record or 404 if the analysis was never saved. Date input accepts an ISO date or datetime. Explicit offsets are converted to UTC for storage. The regression suite exercises successful analysis and replay with a deterministic provider response.

For batch processing, place one JSON object per file in `data/meetings/` or set `INPUT_DIR`. Each object uses the same fields as the API. Run:

```sh
INPUT_DIR=./data/meetings python -m pipeline.process_meetings
```

Batch processing continues after an individual file failure and returns exit status 1 if any file failed.

## Test

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The tests use an ephemeral PostgreSQL instance via `pgserver` or an explicit `TEST_DATABASE_URL` for a disposable PostgreSQL database. An explicit test role needs schema create and drop permissions. Tests isolate each case in its own schema. Provider responses are deterministic and the suite makes no live model calls.

## Limits

- This is a local, unauthenticated transcript-only demo. Audio transcription, search, and calendar integration are roadmap items.
- Model output is validated for shape and types. Review it against the transcript before acting on extracted decisions, assignments, or deadlines.
- Prior records are preserved. Follow-ups were previously transient, so older records return an empty follow-up list. Historic duplicate and orphan rows require a separate data repair. Legacy blank/error analyses require a new ID for a fresh analysis.
- The local regression suite verifies replay, concurrent same-ID persistence, rollback, and the provider error contract. Live model accuracy and latency were unrun.

## License

[MIT](LICENSE.txt)


