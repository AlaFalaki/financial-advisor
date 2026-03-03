# financial-advisor

MVP implementation for the Advisor-in-the-loop Retirement Drawdown Assistant.

## Backend (FastAPI)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload --log-level debug
```

Set OpenAI config in `.env` at repo root:
```
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_SMALL_MODEL=gpt-4o-mini
AUTH_PASSCODE=your_passcode
AUTH_API_KEY=your_api_key
```

## ChromaDB Ingestion Pipeline

CLI (text/markdown files):
```bash
python -m backend.kb_ingest path/to/doc.txt \
  --collection kb_docs \
  --metadata '{"title":"CRA OAS Guide","source_ref":"CRA-OAS-01","source_type":"KB"}' \
  --chunk-size 400 \
  --chunk-overlap 50 \
  --tokenizer-model gpt-4o-mini
```

## Frontend (NuxtJS)

```bash
cd app/frontend
npm install
npm run dev
```

Open:
- User view: http://localhost:3000/user/chat-intake
- Advisor view: http://localhost:3000/advisor/queue
