# EcoOps AI

## Project title
EcoOps AI — Agentic Environmental Response System for campus waterlogging and flood risk.

## Problem
Campuses are exposed to heavy rain, blocked drainage, and flood-prone low-lying areas. Without a fast, clear operational picture, teams react too late and student safety is put at risk.

## Solution
EcoOps AI evaluates user-submitted or simulated environmental inputs with deterministic flood-risk thresholds, stores qualifying incidents, retrieves local campus guidance, and supports operator review before notification. It does not connect to a live sensor feed by default.

## Architecture
- Frontend: React + Vite operations console, with Lucide React icons
- Backend: FastAPI + Pydantic + Uvicorn
- Risk logic: deterministic Python scoring
- AI layer: optional AWS Bedrock interpretation or explicitly labeled local mock
- Storage: local JSON by default, DynamoDB-ready repository abstraction
- Notifications: local mock or SNS-ready abstraction
- RAG: sample campus guidance documents and retrieval abstraction

## Workflow
Submitted input -> deterministic risk assessment -> impact analysis -> local document retrieval -> response plan -> human approval -> optional SNS notification

## Workflow transparency
- The control tower records the stages executed by a sequential Python workflow. It is not a Strands Agents runtime or a collection of autonomous agents.
- Risk severity is calculated in Python. AI interpretation cannot set risk severity or probability.
- High and critical incidents wait for operator approval before notification. With SNS disabled, notification is labeled simulated; configured SNS failures are recorded as failed.
- Local retrieval uses a token-overlap heuristic. Its relevance value is not a semantic-search confidence score. Evidence citations are limited to documents actually returned by retrieval.
- Incident tasks, execution traces, and audit events are stored with local incident records. Analytics only aggregate persisted records.
- The campus risk map is a labeled schematic based on the repository's campus document, not a geographic map. No coordinates or live sensor values are asserted.

## Scenario model
- The simulator calls the deterministic risk engine and does not persist incidents, call Bedrock, or send notifications.
- Rainfall thresholds are 40 mm (medium), 80 mm (high), and 100 mm (critical); observed water-level thresholds are 40%, 70%, and 90%.
- Forecast adjustment is 0 points for normal, 5 for watch, 10 for heavy, and 20 for extreme.
- Drainage adjustment is `max(0, (100 - capacity) * 0.15 + blockage * 0.15)` points. Adjusted water level is capped at 100 before applying the existing thresholds.
- The legacy API field named `probability` is retained for compatibility. It is a rule-derived score, not a calibrated probability; the operations console does not present it as one.

## AWS services
- Amazon Bedrock: AI reasoning and response planning
- Amazon S3: future environmental dataset and document storage
- Amazon DynamoDB: incident persistence
- Amazon SNS: alerting to campus operations
- AWS Lambda: deployable risk function
- API Gateway: public HTTP exposure for the backend
- CloudWatch: structured logs

All AWS integrations are optional and disabled by default. Enabling Bedrock, DynamoDB, or SNS requires AWS credentials, applicable model access/IAM permissions, and may incur AWS usage charges. No AWS infrastructure is provisioned by this project. S3, Lambda, and API Gateway are architecture targets only, not currently connected runtime paths.

## Local setup
1. Clone the repo.
2. Create a Python virtual environment.
3. Install backend dependencies:
   `pip install -r requirements.txt`
4. Install frontend dependencies:
   `cd frontend && npm install`
5. Copy `.env.example` to `.env` and fill in values as needed.

## AWS setup
- Configure AWS credentials using AWS CLI or environment variables.
- Set `AWS_AI_ENABLED=true` and `AWS_BEDROCK_MODEL_ID` to use Bedrock.
- Set `AWS_DYNAMODB_ENABLED=true` and `AWS_SNS_ENABLED=true` when ready to integrate with cloud services.
- For S3, set `AWS_S3_BUCKET` before using cloud storage.

## Environment variables
See `.env.example` for the required variables.

## Running frontend
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

## Running backend
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

## API documentation
FastAPI automatically serves Swagger at:
- http://localhost:8000/docs
- http://localhost:8000/redoc

Key endpoints:
- `GET /api/health`
- `POST /api/sensors/ingest` (typed environmental sensor ingestion)
- `GET /api/sensors` and `GET /api/sensors/latest`
- `POST /api/analyze`
- `GET /api/incidents`
- `POST /api/simulate`
- `GET /api/monitor` (live telemetry with clearly labeled demo fallback)
- `POST /api/scenarios/simulate` (side-effect-free what-if run)
- `GET /api/executions` and `GET /api/executions/{execution_id}`
- `GET /api/incidents/{incident_id}`
- `POST /api/incidents/{incident_id}/approve`
- `PATCH /api/incidents/{incident_id}/tasks/{task_id}`
- `GET /api/knowledge`
- `GET /api/analytics` and `GET /api/analytics/incidents.csv`

## Sensor Ingestion & Live Monitor
EcoOps AI supports a typed, validated environmental sensor ingestion slice with device and timestamp provenance:
- **Endpoint**: `POST /api/sensors/ingest`
- **Payload fields**:
  - `sensor_id` (string, required): Hardware identifier (e.g. `SEN-GATE-01`)
  - `source` (string, optional): Telemetry source or network provenance (e.g. `campus_iot_mesh`)
  - `location` (string, required): Monitored campus area
  - `rainfall` (float, required): Rainfall intensity in mm (0 to 200)
  - `water_level` (float, required): Standing water level percentage (0 to 200)
  - `forecast` (string, optional): Forecast severity (`normal`, `watch`, `heavy`, `extreme`)
  - `timestamp` (string/datetime, optional): Device measurement timestamp provenance
  - `drainage_capacity`, `drainage_blockage` (float, optional): Capacity and blockage metrics
- **Persistence**: Persisted locally in `data/sensor_observations.json` with generated server `ingested_at` timestamp.
- **Live Monitor integration**:
  - When observations are ingested, **Live Monitor** dynamically displays active sensor telemetry, live readings, and provenance metadata.
  - When no observations are present, **Live Monitor** displays a clearly labeled **Demo Fallback Mode** referencing stored local scenario inputs.
- **Example ingestion curl**:
  ```bash
  curl -X POST http://localhost:8000/api/sensors/ingest \
    -H "Content-Type: application/json" \
    -d '{
      "sensor_id": "SEN-GATE-01",
      "source": "campus_iot_mesh",
      "location": "Gate 2",
      "rainfall": 58.5,
      "water_level": 42.0,
      "forecast": "watch"
    }'
  ```

## Demo instructions
1. Start the backend and frontend.
2. Overview shows only stored incident and analysis data; the Live Monitor labels local/demo inputs and reports that sensors are not configured.
3. Risk Simulator lets you change rainfall, water level, forecast severity, and drainage inputs, then compare up to four side-effect-free runs.
4. Incident Command supports review, approval/rejection, audit history, and task status tracking. Tasks cannot enter execution states until approved.
5. Agent Control Tower shows actual stage records, inputs, outputs, timestamps, and retrieved source names. Knowledge & Evidence displays repository documents and stored incident references.
6. Analytics & Audit can export stored incident summaries to CSV.

## Future improvements
- Real Bedrock reasoning with retrieval-enhanced campus context
- DynamoDB-backed incident persistence
- S3 upload for environmental datasets and reports
- More complete agent orchestration with human review workflow
- API Gateway and Lambda deployment packaging

## Team section
- EcoOps AI team
- Built for the WeMakeDevs x AWS Environmental Hacks 2026 challenge

## License
Hackathon project demo.
