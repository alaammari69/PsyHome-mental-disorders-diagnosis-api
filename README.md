# Mental Disorders Diagnosis API 🧠

The backend AI engine powering **PsyHome** — an agentic system for psychiatric symptom extraction and mental disorder diagnosis.

## About

This API serves as the intelligent core of the PsyHome platform. It uses a multi-agent architecture powered by LangChain to conduct conversational psychiatric assessments, extract symptoms from patient dialogue, and generate diagnoses based on collected clinical data.

## Architecture

The system is built around two specialized AI agents:

- **SymptomExtractionAgent** — Engages the patient in a structured conversation to extract and record symptoms in real time.
- **DiagnosisAgent** — Analyzes the full conversation history, patient profile, and extracted symptoms to generate a clinical diagnosis.

!!! **DATABASE IMAGE LINK**: https://drive.google.com/drive/folders/1e_Uk1bOTzDbaEE61KDfU5WlK4aEYQEFH?usp=sharing

## Tech Stack

- **Language:** Python
- **AI / LLM Framework:** LangChain (`langchain-core`)
- **Embeddings:** HuggingFace (`sentence-transformers`)
- **Environment Management:** `python-dotenv`

## Project Structure

```
mental-disorders-diagnosis-api/
├── agents/
│   ├── diagnosis_agent.py          # Generates diagnosis from patient data
│   └── symptom_extraction_agent.py # Conducts conversational symptom extraction
├── core/                           # Core logic and configuration
├── embedder/
│   └── embedders.py                # HuggingFace embedding utilities
├── ml_models/                      # Machine learning model files
├── models/
│   └── context_classes.py          # Data models (PatientContext, etc.)
├── prompts/                        # LLM prompt templates
├── repository/
│   ├── diagnosisdao.py             # Diagnosis database access
│   ├── patient_dao.py              # Patient data access
│   └── patient_symptoms_dao.py     # Patient symptoms data access
├── services/                       # Business logic services
└── main.py                         # Entry point
```

## How It Works

1. A `PatientContext` is initialized with a user ID and thread ID.
2. The **SymptomExtractionAgent** starts a conversation with the patient, extracting symptoms until the session is complete.
3. Once the conversation ends, the **DiagnosisAgent** loads the patient's profile, chat history, and extracted symptoms.
4. A diagnosis is generated and persisted to the database via `DiagnosisDAO`.

## Getting Started

### Prerequisites

- Python 3.9+
- A `.env` file with required environment variables (LLM API keys, database config, etc.)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/alaammari69/mental-disorders-diagnosis-api.git
   cd mental-disorders-diagnosis-api
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Fill in your API keys and DB config
   ```

4. Run the application:
   ```bash
   python main.py
   ```

## Related Projects

- [PsyHome Android App](https://github.com/alaammari69/event-mate) — The mobile front-end that consumes this API.

## License

This project is part of the PsyHome capstone project. All rights reserved.
