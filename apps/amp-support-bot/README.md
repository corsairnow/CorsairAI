# AMP_Support_Bot (FastAPI • Ollama • Chroma • pyproject.toml)

Grounded **RAG support bot** with folder-based ingestion, versioned KBs, strict grounding, and per‑chat history.
**Dependency management:** `pyproject.toml` (no requirements.txt).



## 1) Prereqs & Python Version

- **Python:** 3.10 or newer (3.10–3.12 recommended). Check:
  ```bash
  python3 --version
  # Must print: Python 3.10.x (or higher)
  ```
- **Ollama** running locally with models pulled:
  ```bash
  ollama serve
  ollama pull llama3:8b
  ollama pull mxbai-embed-large
  ```

---

## 2) Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -U pip

# Install via pyproject.toml (editable mode is fine for dev)
pip install -e .
```

Optional: copy `.env.example` → `.env` and adjust (Ollama URL, model names, paths).

---

## 3) Ingest — where to put files & how to run

1) Place your Markdown files in a **folder** under:
```
root/uploads/<folder_name>/*.md
```
For example:
```
root/uploads/amplivo_comp_plan_md/overview.md
root/uploads/amplivo_comp_plan_md/rank_requirements.md
```

2) Start the API:
```bash
./run.sh
# serves on http://localhost:1060
```

3) Ingest the folder:
```bash
curl -sS -X POST http://localhost:1060/kb/ingest   -H 'Content-Type: application/json'   -d '{"folder_name":"amplivo_comp_plan_md"}' | jq
```

This creates a **versioned KB** under `root/kb/<kb_id>/versions/<kb_version_id>/` and a Chroma collection in `root/chroma`.



## 4) Test the app (curl)

**Health & version**
```bash
curl -sS http://localhost:1060/healthz | jq
curl -sS http://localhost:1060/version | jq
```

**List KBs**
```bash
curl -sS http://localhost:1060/kb | jq
```

**Inspect a KB**
```bash
curl -sS http://localhost:1060/kb/amplivo_comp_plan_md | jq
```

**Start a chat (answers strictly from the ingested KB)**
```bash
curl -sS -X POST http://localhost:1060/chat/start   -H 'Content-Type: application/json'   -d '{
        "kb_ids":["amplivo_comp_plan_md"],
        "message":"How much BV do I need to reach 1 Star?",
        "language":"en",
        "stream":false
      }' | jq
```

**Continue the chat**
```bash
curl -sS -X POST http://localhost:1060/chat/reply   -H 'Content-Type: application/json'   -d '{
        "chat_id":"00042-8f19a3d2",
        "message":"Clarify the two-leg requirement.",
        "stream":false
      }' | jq
```

**Fetch transcript**
```bash
curl -sS http://localhost:1060/chat/00042-8f19a3d2 | jq
```

**Delete KB (soft/hard)**
```bash
curl -sS -X DELETE "http://localhost:1060/kb/amplivo_comp_plan_md" | jq
curl -sS -X DELETE "http://localhost:1060/kb/amplivo_comp_plan_md?force=true" | jq
```

---

## 5) Behavior & Storage

- Strict grounding to the **pinned KB versions** selected at chat start.
- Sources & index: `root/kb/<kb_id>/versions/<kb_version_id>/{source,index}`
- Chroma persistence: `root/chroma`
- Chat history: `root/chats/sessions.sqlite`

If retrieval confidence is low, responses politely abstain and include nearest citations.

---

## 6) Config (via .env)

```
OLLAMA_BASE_URL=http://127.0.0.1:11434
EMBED_MODEL=mxbai-embed-large
CHAT_MODEL=llama3:8b
DATA_ROOT=./root
CHROMA_DIR=./root/chroma
```
