
# Amp_SQL_Gen (macOS • Homebrew ready)

Natural-language → SQL compiler service using **Ollama** models. **Compile-only** — this app never touches your DB.
- **Endpoint:** `POST /nl2sql/compile`
- **Returns:** `{ sql, model, validators, explanation }`
- **Port:** `1050`
- **Schema file:** `./schema/schema.yaml` (edited by developers, hot-reloaded on change)

> Assumes macOS with **Homebrew installed** and you prefer a **Python virtualenv** workflow. The style mirrors the translator README.  fileciteturn0file0

---

## 1) Install tools with Homebrew

**Install Python 3.12, jq (pretty JSON), and Ollama (model runtime).**
```bash
brew install python@3.12 jq ollama
```
*Installs Python, jq, and the local model server.*

**Start Ollama (background).**
```bash
brew services start ollama
```
*Runs `ollama serve` on `http://127.0.0.1:11434`.*

**Pull the SQL models.**
```bash
ollama pull llama-3-sqlcoder-8b:latest
ollama pull sqlcoder-best:latest
```
*Downloads both recommended SQL models.*

---

## 2) Create & activate a Python 3.12 venv

**From project root (contains `pyproject.toml`).**
```bash
"$(brew --prefix python@3.12)/bin/python3.12" -m venv .venv
```
*Creates an isolated environment bound to Python 3.12.*

**Activate it.**
```bash
source .venv/bin/activate
```
*Switches your shell to the venv’s Python/pip.*

**Upgrade pip and install.**
```bash
python -m pip install -U pip
python -m pip install -e .
```
*Installs dependencies (FastAPI, sqlglot, etc.).*

---

## 3) Configure the schema

Edit `./schema/schema.yaml` to match your analytics views/tables. A starter example is provided.
This service **hot‑reloads** the schema when the file’s modified time changes; no restart needed.

**Example `schema/schema.yaml`:**
```yaml
dialect: postgres
timezone: UTC
tables:
  - name: users
    columns: [id, email, country, created_at]
  - name: orders
    columns: [id, user_id, bv, created_at]
joins:
  - left: orders.user_id
    right: users.id
```

---

## 4) Run the API server (dev)

**Start FastAPI with Uvicorn (auto-reload).**
```bash
python -m uvicorn amp_sql_gen.app:app --host 0.0.0.0 --port 1050 --reload
```
*Serves the API on `http://localhost:1050`.*

---

## 5) Test the API (curl)

**Health check**
```bash
curl -sS http://localhost:1050/healthz | jq .
```

**Version**
```bash
curl -sS http://localhost:1050/version | jq .
```

**Compile with `llama-3-sqlcoder-8b:latest`**
```bash
curl -sS -X POST http://localhost:1050/nl2sql/compile   -H 'Content-Type: application/json'   -d '{
    "question": "Total BV per country in last 30 days, highest first",
    "dialect": "postgres",
    "model": "llama-3-sqlcoder-8b:latest"
  }' | jq .
```

**Compile with `sqlcoder-best:latest`**
```bash
curl -sS -X POST http://localhost:1050/nl2sql/compile   -H 'Content-Type: application/json'   -d '{
    "question": "Top 10 partners by orders this month",
    "dialect": "postgres",
    "model": "sqlcoder-best:latest"
  }' | jq .
```

> The service returns SQL only; your Laravel layer should preview and execute with **read‑only creds** and **row/time limits**.

---

## 6) Models & policies

- Allowed models: `llama-3-sqlcoder-8b:latest`, `sqlcoder-best:latest` (reject others).
- Deterministic generation: **temperature = 0**.
- Validator checks before returning:
  - parses with `sqlglot`
  - **SELECT-only**
  - **no `SELECT *`**
  - **LIMIT ≤ 200** (auto‑add if missing)
  - tables used ⊆ schema tables

---

## 7) Troubleshooting

**Model not found / runner crash**
```bash
brew services restart ollama
ollama pull llama-3-sqlcoder-8b:latest
ollama pull sqlcoder-best:latest
```
*Restarts the runtime and ensures models are present.*

**Module not found**
```bash
python -m pip install -e .
```
*Install from project root.*

**Wrong Python version**
```bash
deactivate; rm -rf .venv
"$(brew --prefix python@3.12)/bin/python3.12" -m venv .venv
source .venv/bin/activate; python -V
```

---

## Notes for production

- This dev service is open; add **JWT/mTLS + rate limits** before exposing.
- Use **views** with RLS/tenant filters; run queries with a **read‑only role**.
- Log `{user_id, question, model, sql, schema_version, validators}` for audit.
