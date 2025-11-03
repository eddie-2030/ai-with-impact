# Example cURL requests

# 1) Ingest / index templates (with LLM embeddings)
curl -X POST http://localhost:8000/ingest

# 2) Analyze a contract with LLM-powered AI analysis
curl -X POST http://localhost:8000/analyze \
  -F "template_name=master_service_agreement" \
  -F "file=@data/contracts/sample_contract_acme.md"

# 3) Analyze against standard terms template
curl -X POST http://localhost:8000/analyze \
  -F "template_name=standard_terms" \
  -F "file=@data/contracts/sample_contract_acme.md"
