# Bring Books to Life 🎭 — Auto Persona PDF Chat

Upload a persona PDF and the Streamlit chat initializes automatically. The app reads the persona profile, derives a default character name from the filename, includes the extracted profile in the system prompt, and uses a retrieval index to ground responses in a document.

## Recommended document setup

- **Persona profile PDF** (required): identity, personality, background, speaking style, behavior rules.
- **Knowledge PDF/TXT** (optional): the book or reference material the persona should use for factual answers.
- If no separate knowledge source is uploaded, the persona PDF is also used as the retrieval source.

This separation is recommended because a persona profile tells the model *how to behave*, while the knowledge source tells it *what facts to use*.

## Setup (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set your key:

```dotenv
GROQ_API_KEY=your_actual_groq_api_key
```

Run the app:

```powershell
streamlit run app.py
```

## Features

- Auto-initialize chat when a persona file is uploaded (no Start Chat button).
- PDF and TXT uploads.
- Optional separate knowledge document.
- Character name inferred from the persona filename, e.g. `Sherlock_Holmes_Persona.pdf` → `Sherlock Holmes`.
- Persona profile text passed as system-level character guidance.
- LangGraph agent, Groq LLM, local FastEmbed embeddings, FAISS retrieval, and in-memory per-chat conversation memory.
- Uploaded file signature prevents rebuilding the vector index on every chat rerun.

## Limitations and production recommendations

- PDFs must contain selectable text; scanned PDFs require OCR.
- This version uses the filename as a default persona name rather than using a second LLM call to extract structured metadata. Rename the file clearly or customize `infer_persona_name()` if needed.
- The extracted persona profile is limited to the first 18,000 characters in the system prompt. Keep the profile concise and specific.
- The checkpointer and vector index are in memory. Add persistent storage for deployed multi-user applications.
- Add upload-size limits, MIME/file validation, privacy controls, and tests before production deployment.
- Never allow document text to override system-level safety or application instructions.

## Project files

- `app.py` — auto-start Streamlit UI and chat history.
- `agent.py` — LangGraph agent, persona prompt, and conversation memory.
- `personas.py` — default persona fallback.
- `rag.py` — PDF/TXT extraction, chunking, embeddings, and FAISS retrieval.
- `tools.py` — book search tool.
- `run.py` — command-line runner.
- `test_offline.py` — retrieval checks.
