# Amp_Translator (macOS • Homebrew ready)

Minimal FastAPI translation microservice using **Llama 3** via **Ollama**.  
- **Endpoint:** `POST /translate`  
- **Returns:** `{ "translated_text": "..." }`  
- **Port:** `1040`  
- **No UI.** Dev-only by default (open API; add auth before prod).

**Assumptions:** You’re on macOS, **Homebrew is already installed and working**, and you prefer a **Python virtualenv** workflow.

---

## 1) Install required tools with Homebrew

**Install Python 3.12, jq (pretty JSON), and Ollama (model runtime).**
```bash
brew install python@3.12 jq ollama
```
*Installs a modern Python, jq, and the local model server.*

**Start Ollama in the background (recommended).**
```bash
brew services start ollama
```
*Runs the model server on `http://127.0.0.1:11434` without needing an open terminal.*

**Pull the Llama 3 model (first time only).**
```bash
ollama pull llama3
```
*Downloads the model used for translation.*

---

## 2) Create and activate a Python 3.12 virtualenv (venv)

**From your project root (contains `pyproject.toml`), create a new venv pinned to 3.12.**
```bash
"$(brew --prefix python@3.12)/bin/python3.12" -m venv .venv
```
*Creates an isolated environment at `.venv`.*

**Activate the venv.**
```bash
source .venv/bin/activate
```
*Switches your shell to use the venv’s Python and pip.*

**Confirm Python version.**
```bash
python -V
```
*Should show `Python 3.12.x`.*

---

## 3) Install the service into the venv

**Upgrade pip.**
```bash
python -m pip install -U pip
```
*Keeps the installer current.*

**Install this package (editable mode).**
```bash
python -m pip install -e .
```
*Installs dependencies (FastAPI, Uvicorn, httpx, etc.) and registers `amp_translator`.*

---

## 4) Run the API server (dev)

**Start FastAPI with Uvicorn (auto-reload).**
```bash
python -m uvicorn amp_translator.app:app --host 0.0.0.0 --port 1040 --reload
```
*Serves the API on `http://localhost:1040` and reloads on changes.*

---

## 5) Test the API (curl)

**Health check.**
```bash
curl -sS http://localhost:1040/healthz | jq .
```
*Confirms the service is running.*

**Version.**
```bash
curl -sS http://localhost:1040/version | jq .
```
*Shows the service version.*

**Translate (auto-detect ➜ English).**
```bash
curl -sS -X POST http://localhost:1040/translate   -H 'Content-Type: application/json'   -d '{"text":"สวัสดีครับ ยินดีที่ได้รู้จัก","target_lang":"English"}' | jq .
```
*Thai → English example.*

**Translate (explicit French ➜ English).**
```bash
curl -sS -X POST http://localhost:1040/translate   -H 'Content-Type: application/json'   -d '{"text":"Bonjour tout le monde","source_lang":"French","target_lang":"English"}' | jq .
```
*Adds a source-language hint (optional).*

**English ➜ Thai.**
```bash
curl -sS -X POST http://localhost:1040/translate   -H 'Content-Type: application/json'   -d '{"text":"Please confirm your account details by Friday.","target_lang":"Thai"}' | jq .
```
*Common English → Thai flow.*

> If `jq` is missing or you prefer plain output, omit the `| jq .` part.

---

## 6) Stop services

**Stop the API server.**
```bash
# Press Ctrl + C in the terminal running uvicorn
```
*Gracefully stops FastAPI.*

**Stop Ollama background service (optional).**
```bash
brew services stop ollama
```
*Shuts down the model server started by Homebrew.*

---

## Troubleshooting (quick)

**`ModuleNotFoundError: amp_translator`**
```bash
python -m pip install -e .
```
*Run from the project root containing `pyproject.toml`.*

**Wrong Python version after activation**
```bash
deactivate; rm -rf .venv
"$(brew --prefix python@3.12)/bin/python3.12" -m venv .venv
source .venv/bin/activate; python -V
```
*Recreate the venv with the explicit 3.12 binary.*

**Model connection errors**
```bash
brew services start ollama; ollama pull llama3
```
*Ensure Ollama is running and the `llama3` model is available.*

---

## Notes for production (later)

- Add **JWT/mTLS + rate limits** before exposing publicly.  
- Consider a reverse proxy (nginx/traefik) and disable `--reload`.  
- Pin model tags and dependency versions for reproducibility.
