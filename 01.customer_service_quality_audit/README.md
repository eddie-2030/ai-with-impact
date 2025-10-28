# Customer Service QA – Reference Implementation

This repo processes customer conversations, anonymizes text, scores quality with an LLM (or a heuristic fallback), stores results in Postgres, exposes a FastAPI scoring endpoint, and visualizes insights in Streamlit.

## License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.

## Quick Start (Docker Compose)

```bash
cp .env.example .env
# edit .env if using OpenAI (set OPENAI_API_KEY and LLM_BACKEND=openai)

# Start DB, API, Dashboard
cd ops/docker
docker compose up --build
```

- API: http://localhost:8000/docs
- Dashboard: http://localhost:8501

## Score a Conversation (Example)

```bash
curl -X POST http://localhost:8000/score   -H 'Content-Type: application/json'   -d '{
    "conversation_id": "conv-001",
    "agent_id": "agent-42",
    "agent_name": "Alex",
    "started_at": "2025-10-01T10:00:00",
    "channel": "chat",
    "language": "en",
    "transcript": "Customer: my order #1234 is missing. Agent: I\'m sorry for the trouble; let me verify your account. I\'ve issued a refund and escalated your shipping issue."
  }'
```

## Batch Pipeline

Drop JSON files like `data/conversations/conv-*.json`:

```json
{
  "conversation_id": "conv-002",
  "agent_id": "agent-7",
  "agent_name": "Jamie",
  "started_at": "2025-10-01T11:00:00",
  "channel": "call",
  "language": "en",
  "transcript": "..."
}
```

Then run:

```bash
python -m pipeline.process_conversations
```

## Calibration & Evaluation

Collect a CSV with columns: `conv_id, prof_h, frnd_h, res_h, prof_m, frnd_m, res_m` (human vs model).
Fit calibrators and compute metrics using `eval/` utilities (examples omitted for brevity).

## Notes
- Replace heuristic backend with `LLM_BACKEND=openai` for higher fidelity.
- Extend anonymizer with entity models if needed.
- Add multilingual prompts or fine-tuning for domain.
