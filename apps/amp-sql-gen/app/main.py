from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from . import __version__
from .config import settings, allowed_models
from .schema import SchemaRegistry
from .validator import validate_sql
from .llm import generate_sql
from .postproc import extract_sql
import httpx
import traceback

app = FastAPI(title="Amp_SQL_Gen", version=__version__)

schema = SchemaRegistry(settings.SCHEMA_PATH)

class CompileRequest(BaseModel):
    question: str = Field(..., min_length=3, description="Natural language question/task")
    dialect: Optional[str] = Field(default=None, description="SQL dialect eg. 'mysql'")
    model: Optional[str] = Field(default=None, description="Model tag, e.g., 'llama-3-sqlcoder-8b:latest'")

class CompileResponse(BaseModel):
    sql: str
    model: str
    validators: Dict[str, Any]
    explanation: Optional[str] = None

@app.get("/healthz")
async def healthz():
    schema.reload_if_changed()
    return {"status": "ok test", "service": "Amp_SQL_Gen", "version": __version__}

@app.get("/version")
async def version():
    return {"version": __version__}

@app.get("/schema")
async def schema_info():
    schema.reload_if_changed()
    return {"path": settings.SCHEMA_PATH, "dialect": schema.dialect, "tables": sorted(schema.tables)}

@app.post("/nl2sql/compile", response_model=CompileResponse)
async def nl2sql_compile(body: CompileRequest):
    schema.reload_if_changed()

    mdl = (body.model or settings.DEFAULT_MODEL).strip()
    if mdl not in allowed_models():
        raise HTTPException(status_code=400, detail=f"Unsupported model. Allowed: {', '.join(sorted(allowed_models()))}")

    dialect = (body.dialect or schema.dialect or "mysql").lower()
    # limit_max = settings.LIMIT_MAX
    try:
        print("sql")
        raw = await generate_sql(
            model=mdl,
            question=body.question,
            dialect=dialect,
            schema_text=schema.render_for_prompt(),
        )
        if not raw:
            raise HTTPException(status_code=502, detail="Empty output from model.")
    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response else "N/A"
        preview = e.response.text[:500] if e.response else ""
        raise HTTPException(status_code=502, detail=f"Ollama returned {status}: {preview}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Ollama request error: {e.__class__.__name__}: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream model error: {e.__class__.__name__}: {e}")

    sql = extract_sql(raw)
    if not sql:
        raise HTTPException(status_code=502, detail="Failed to extract SQL from model output.")

    v = validate_sql(sql, dialect=dialect, allowed_tables=schema.tables)
    if v.get("parse_ok") and not v.get("limit_ok") and v.get("select_only", False):
        candidate = sql.rstrip().rstrip(";")
        v2 = validate_sql(candidate, dialect=dialect, allowed_tables=schema.tables)
        if v2.get("parse_ok") and v2.get("limit_ok"):
            sql = candidate
            v = v2

    explanation = None
    return CompileResponse(sql=sql, model=mdl, validators=v, explanation=explanation)

@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    print("UNHANDLED EXCEPTION:", exc)
    return JSONResponse(status_code=502, content={"detail": f"Unhandled error: {exc.__class__.__name__}"})
