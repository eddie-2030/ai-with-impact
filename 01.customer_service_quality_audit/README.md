# Customer Service Quality Audit

This reference implementation redacts common contact details from customer transcripts, scores professionalism, friendliness, and resolution effectiveness, stores the result in PostgreSQL, and serves it through a FastAPI endpoint and Streamlit dashboard. The default heuristic scorer works locally without an external model. The optional OpenAI scorer sends redacted transcript text to the configured API.

## Architecture

The scoring API and batch pipeline both anonymize transcripts before scoring. They store the original and redacted transcript with the agent and conversation records, then persist the three dimensions and an explanation in `scores`. The dashboard joins conversations to agents and scores. Its overall score is the unweighted mean of the three dimensions and remains blank until all three are present. Conversations without scores remain visible.

## Run with Docker Compose

Copy the example configuration and start the database, API, and dashboard from this directory:

```bash
cp .env.example .env
docker compose -f ops/docker/docker-compose.yml up --build -d
```

The heuristic backend needs no credentials. To use the OpenAI backend, set `LLM_BACKEND=openai` and provide a valid `OPENAI_API_KEY` in `.env`. Keep `.env` private and do not commit it. The database is available to the host on port `5433`. The containers use their private Compose network.

- API documentation: <http://localhost:8000/docs>
- Dashboard: <http://localhost:8501>
- Stop services: `docker compose -f ops/docker/docker-compose.yml down`
- Stop and remove the development database volume: add `-v` to the `down` command.

## Score a conversation

With the services running, submit a new conversation. The transcript is redacted before it is sent to the scorer.

```bash
curl --fail-with-body http://localhost:8000/score \
  -H 'Content-Type: application/json' \
  -d '{
    "conversation_id": "conv-demo-001",
    "agent_id": "agent-demo",
    "agent_name": "Alex",
    "started_at": "2026-11-05T10:00:00",
    "channel": "chat",
    "language": "en",
    "transcript": "I am sorry about the delay. I verified the order and issued a refund."
  }'
```

Refresh the dashboard to see the three dimension scores and their calculated overall mean. Conversation IDs are unique, so use a new ID for each request.

## Run the batch pipeline

Place JSON records in `data/conversations/` with the fields `conversation_id`, `agent_id`, `transcript`, and optionally `agent_name`, `started_at`, `channel`, and `language`. Copy records into the running API container, then start the batch:

```bash
docker compose -f ops/docker/docker-compose.yml cp data/conversations/. api:/app/data/conversations/
docker compose -f ops/docker/docker-compose.yml exec api \
  python -m pipeline.process_conversations
```

The batch command processes every JSON file in `INPUT_DIR` (default `./data/conversations/`). Processed records are not removed. Because conversation IDs are unique, avoid rerunning a batch against records already stored.

## Tests and evaluation

From this project directory, install `requirements.txt`, then run:

```bash
python -m unittest discover -s tests -v
```

Run the dashboard query regression from this project directory with `python -m unittest tests.test_dashboard_query -v`. It uses an in-memory SQLite fixture to check stored score names, the calculated overall score, ordering, and unscored conversations. The separate metrics test uses pytest. `eval/metrics.py` and `eval/calibration.py` contain evaluation helpers. Calibration requires a labeled CSV with columns `conv_id, prof_h, frnd_h, res_h, prof_m, frnd_m, res_m`.

## Limitations

- The heuristic scores are example rules and are not validated quality measurements. Calibrate and evaluate against representative human labels before using scores for consequential decisions.
- The OpenAI backend currently uses `gpt-4o-mini` and has no retry, timeout, or custom model configuration.
- Redaction uses regular expressions and can miss sensitive information or redact ordinary text. Review the approach against your privacy requirements.
- The API stores the original transcript as well as redacted text. Define access controls and retention before using real customer data.
- Compose starts application services before PostgreSQL is necessarily ready. The API creates tables at startup but does not retry a database connection failure.

If the API exits while PostgreSQL is starting on a clean boot, wait for the `db` service to become healthy, then run `docker compose -f ops/docker/docker-compose.yml restart api`.

## License

MIT. See [LICENSE.txt](LICENSE.txt).
