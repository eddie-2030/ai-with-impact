# Procurement Contract Analyzer

This FastAPI service extracts clauses from a supplier contract, compares them with a procurement template using OpenAI embeddings, and returns a model-generated risk summary, deviations, and recommendations.

## Run locally

Use Python 3.12 from this project directory.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open [the API explorer](http://127.0.0.1:8000/docs). Startup and offline tests need no key. For live analysis, copy `.env.example` to the ignored `.env`, set `OPENAI_API_KEY`, and restart the server. The defaults are `text-embedding-3-small` and `gpt-4o-mini`. Override them with `OPENAI_EMBEDDING_MODEL` and `OPENAI_CHAT_MODEL`. `DATA_DIR` defaults to `data` and must contain the templates.

## Analyze a contract

```bash
curl --fail-with-body http://127.0.0.1:8000/analyze \
  -F 'template_name=master_service_agreement' \
  -F 'file=@data/contracts/sample_contract_acme.md'
```

You can also choose `standard_terms`. A successful response includes the template, risk band, clause findings, and recommendations. The live example sends the sample contract to OpenAI and can incur charges.

For an offline smoke check, send invalid PDF content and expect HTTP 422.

```bash
printf 'invalid PDF' | curl -sS -i http://127.0.0.1:8000/analyze \
  -F 'file=@-;filename=invalid.pdf'
```

## Data flow and upload rules

- `POST /analyze` accepts a PDF, DOCX, UTF-8 TXT, or UTF-8 Markdown file with a 10 MiB limit.
- The service parses each document independently before making model calls. Unsupported formats return 415. Oversized files or DOCX archives return 413. Corrupt or unreadable documents return 422. DOCX archives are limited to 50 MiB of declared expanded content and 2,000 entries.
- The first valid analysis builds the template index in memory. `POST /ingest` reloads the trusted local templates and rebuilds that index. The retriever embeds the contract clauses and matches them to the selected template. The risk agent uses the contract and matches to produce a JSON report.

## Tests

```bash
python -m unittest discover -s tests -v
```

The offline suite generates PDF and DOCX fixtures and exercises the upload endpoint with a deterministic provider substitute. `test_llm_workflow.py` is a separate live smoke script that can incur charges.

## Limitations

Scanned PDFs require OCR outside this service. The 10 MiB file limit applies after multipart parsing. Configure a request body limit, timeouts, and access controls at the proxy before deployment. A file size limit alone does not cap PDF parser CPU and memory use. Contract text goes to the configured provider during live analysis. Review the provider's data handling before sending confidential documents and have a qualified reviewer verify the findings.

See the [technical overview](WORKFLOW_AND_TECHNICAL_OVERVIEW.md) and [example requests](examples/curl_requests.md).
