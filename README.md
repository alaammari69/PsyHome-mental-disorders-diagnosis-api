# PsyHome: AI Diagnostic Engine 🧠

The backend AI engine powering **PsyHome**, an agentic platform for AI-assisted psychiatric symptom extraction and diagnosis support. Built as a final-year engineering capstone project (graded *Excellent*), PsyHome demonstrates how a multi-agent LLM pipeline can conduct structured clinical conversations, ground its reasoning in the DSM-5, and produce validated diagnostic output for review by a licensed psychiatrist.

> **Status:** advanced prototype, not a shipped/production product. Built as an academic capstone (PFE) to demonstrate an end-to-end agentic architecture, not to be used for real clinical decisions.

## Part of the PsyHome Platform

This repo is the AI core. The full system also includes:
- [PsyHome Web Application](https://github.com/alaammari69/PsyHome-web-application): psychiatrist-facing dashboard (React)
- [PsyHome Mobile App](https://github.com/alaammari69/psy-home-mobile-app): patient-facing chat app (React Native / Expo)

## Architecture

The core of the system is a two-agent pipeline built on **LangGraph**, backed by a **RAG pipeline over a DSM-5 knowledge base**:

- **SymptomExtractionAgent**: conducts a structured conversational assessment with the patient, extracting symptoms in real time and scoring each on a 5-level confidence scale (`ABSENT → UNLIKELY → NEUTRAL → LIKELY → CONFIRMED`), rather than a binary present/absent flag.
- **DiagnosisAgent**: once the conversation ends, analyzes the full chat history, patient profile, and extracted symptoms, retrieves relevant DSM-5 context, and produces a **Pydantic-validated structured diagnosis**: not free-text — so output is safe to render directly in the clinician dashboard.

Both agents share a `PatientContext` object that tracks conversation state (extracted symptoms, suspected disorders/symptoms, diagnosis stage) across the session.

## Tech Stack

- **Language:** Python
- **API:** FastAPI
- **Agent Orchestration:** LangGraph, LangChain
- **LLM Providers:** Groq, DeepSeek (pluggable)
- **Embeddings:** HuggingFace (`sentence-transformers`) for the DSM-5 RAG pipeline
- **Database:** PostgreSQL (via `psycopg`), with dedicated DAOs per entity
- **Auth:** JWT, with separate signing secrets per role (psychiatrist / admin / patient)
- **Tracing:** LangSmith

## Project Structure

```
├── agents/
│   ├── symptom_extraction_agent.py   # Conversational symptom extraction
│   └── diagnosis_agent.py            # Structured diagnosis generation
├── core/                             # App configuration (.env lives here)
├── embedder/                         # HuggingFace embedding utilities + DSM-5 embedding scripts
├── ml_models/                        # LLM client configuration
├── models/
│   ├── context_classes.py            # PatientContext, Symptom, Disorder, diagnosis stage
│   ├── custom_enums.py               # SymptomLikelihood confidence scale
│   ├── response_schemas.py           # Pydantic schemas for structured agent output
│   └── tool_arguments_schemas.py
├── prompts/                          # System prompts and templates for both agents
├── repository/                       # DAOs: Patient, PatientThread, PatientSymptom, Diagnosis, Disorder, Psychiatrist...
├── services/
│   └── services.py                   # FastAPI app: routes, auth, CORS
└── main.py                           # CLI entry point for local testing of the agent pipeline
```

## How It Works

1. A `PatientContext` is initialized for a given patient and conversation thread.
2. The **SymptomExtractionAgent** engages the patient in conversation, extracting and scoring symptoms turn by turn until the session naturally concludes.
3. The **DiagnosisAgent** loads the patient's profile, full chat history, and extracted symptoms, retrieves relevant DSM-5 context via the RAG pipeline, and generates a structured diagnosis.
4. The diagnosis is persisted via `DiagnosisDAO` and returned to the psychiatrist-facing dashboard for review.

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL instance
- API keys for your chosen LLM provider(s) (Groq and/or DeepSeek)

### Installation

```bash
git clone https://github.com/alaammari69/PsyHome-mental-disorders-diagnosis-api.git
cd PsyHome-mental-disorders-diagnosis-api
pip install -r requirements.txt
```

Set up environment variables:

```bash
cp core/.env.example core/.env
# Fill in your DB connection, LLM API keys, and JWT secrets
```

Run the API:

```bash
uvicorn services.services:app --reload
```

Or run the agent pipeline directly via CLI (useful for testing agent behavior without the API layer):

```bash
python main.py
```

## Notes

- This is a research/academic prototype. Diagnostic output is intended to support a licensed psychiatrist's review, not to replace one.
- Environment variables in this repo are placeholders for local development only — no third-party API keys are included.

## License

MIT — see [LICENSE](LICENSE).
