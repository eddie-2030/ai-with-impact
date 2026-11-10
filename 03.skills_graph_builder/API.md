# Skills Graph Builder API

Run the API locally at `http://127.0.0.1:8000`. See [README.md](README.md) for setup and offline tests.

| Endpoint | Response or action | Provider use |
| --- | --- | --- |
| `GET /health` | Returns `{"status":"ok"}` when the API process is running | None |
| `GET /roles` | Lists role IDs, titles, levels, and skill requirements | None |
| `GET /persons` | Lists bundled roster entries and profiles ingested in this process | None |
| `GET /person/{person_id}/skills` | Lists current skill edges for a known person. Unprocessed profiles return an empty list | None |
| `POST /ingest/profile` | Extracts and records skills for submitted evidence | Chat and embeddings |
| `GET /roles/matches?person_id=p100&top_k=3` | Returns `role_id`, `title`, `level`, and cosine `score` in ranked order. Profiles without skills return an empty list | Embeddings for profiles with skills |
| `GET /recommendations/p100?role_id=r_data_analyst` | Returns `person_id`, `role_id`, `gaps`, `actions`, and `rationale` | Select a role explicitly to skip model calls. Omitting it uses matching first |

## Ingest a profile

```json
{
  "profile": {"person_id": "example-1", "name": "Synthetic example"},
  "evidence": [{"source": "project", "text": "Built a Python service and queried records with SQL."}]
}
```

A successful response includes `person_id` and `skills_added`. A request with no nonblank evidence stores only profile metadata and returns an empty `skills_added` list. A failed provider call during ingestion leaves the stored profile, skill edges, and evidence vectors untouched.

## Errors

An unknown person or role returns HTTP 404. Asking for an automatic plan before a profile has any skills also returns 404. The health endpoint checks the API process independently of provider availability.

A missing key, timed-out provider call, rate limit, or other provider error returns HTTP 503 for the affected request. The response contains `detail.code` and `detail.message`. For example:

```json
{"detail":{"code":"provider_not_configured","message":"Set OPENAI_API_KEY on the server to enable model requests."}}
```

Handle the error code and display the message. The API does not issue random rankings when the provider fails.
