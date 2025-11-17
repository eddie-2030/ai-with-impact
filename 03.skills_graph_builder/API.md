# API Documentation

## Base URL
```
http://localhost:8000
```

## Endpoints

### Health Check
```http
GET /health
```
**Response:**
```json
{
  "status": "ok"
}
```

### Get All Roles
```http
GET /roles
```
**Response:**
```json
[
  {
    "role_id": "r_data_analyst",
    "title": "Data Analyst",
    "level": "IC3",
    "skills": [
      {
        "skill_id": "sql",
        "label": "SQL",
        "weight": 0.8,
        "must_have": true
      }
    ]
  }
]
```

### Get All People
```http
GET /persons
```
**Response:**
```json
[
  {
    "person_id": "p100",
    "name": "Morgan Lopez",
    "org_unit": "Customer",
    "location": "NYC",
    "role_current": "ML Engineer"
  }
]
```

### Get Person's Skills
```http
GET /person/{person_id}/skills
```
**Example:** `GET /person/p100/skills`

**Response:**
```json
[
  {
    "skill_id": "python",
    "label": "Python",
    "confidence": 0.95,
    "source": "project"
  }
]
```

### Get Role Matches for Person
```http
GET /roles/matches?person_id={person_id}&top_k={number}
```
**Example:** `GET /roles/matches?person_id=p100&top_k=5`

**Response:**
```json
[
  {
    "role_id": "r_ml_eng",
    "title": "ML Engineer",
    "match_score": 0.85,
    "missing_skills": ["docker"],
    "strengths": ["python", "mlops"]
  }
]
```

### Get Learning Recommendations
```http
GET /recommendations/{person_id}?role_id={role_id}
```
**Example:** `GET /recommendations/p100?role_id=r_ml_eng`

**Response:**
```json
{
  "person_id": "p100",
  "role_id": "r_ml_eng",
  "gap_analysis": {
    "missing_skills": ["docker", "kubernetes"],
    "learning_plan": [
      {
        "skill": "docker",
        "priority": "high",
        "estimated_hours": 20,
        "resources": ["Docker documentation", "Hands-on labs"]
      }
    ]
  }
}
```

### Ingest New Profile
```http
POST /ingest/profile
```
**Request Body:**
```json
{
  "profile": {
    "person_id": "p200",
    "name": "John Doe",
    "org_unit": "Engineering",
    "location": "San Francisco",
    "role_current": "Software Engineer"
  },
  "evidence": [
    {
      "text": "Built microservices using Python and Docker",
      "type": "project"
    }
  ]
}
```

**Response:**
```json
{
  "person_id": "p200",
  "skills_added": [
    {
      "skill_id": "python",
      "confidence": 0.9
    }
  ]
}
```

## Error Responses

### 404 Not Found
```json
{
  "detail": "Person not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Role catalog is empty"
}
```

## Rate Limits
- No rate limits currently implemented
- OpenAI API calls are subject to OpenAI's rate limits

## Authentication
- No authentication required for local development
- API key required for OpenAI services (configured via environment variables)
