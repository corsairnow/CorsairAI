from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from .llm import llama3_translate
from . import __version__
import httpx
from langdetect import detect, LangDetectException

app = FastAPI(title="Amp_Translator", version=__version__)

# ---- Translate-only guardrails ----
MAX_TEXT_CHARS = 4000

LANG_CANON = {
    "en": "English", "english": "English",
    "th": "Thai", "thai": "Thai",
    "fr": "French", "french": "French",
    "es": "Spanish", "spanish": "Spanish",
    "de": "German", "german": "German",
    "it": "Italian", "italian": "Italian",
    "pt": "Portuguese", "portuguese": "Portuguese",
    "nl": "Dutch", "dutch": "Dutch",
    "ru": "Russian", "russian": "Russian",
    "zh": "Chinese", "chinese": "Chinese", "zh-cn": "Chinese", "zh-tw": "Chinese",
    "ja": "Japanese", "japanese": "Japanese",
    "ko": "Korean", "korean": "Korean",
    "ar": "Arabic", "arabic": "Arabic",
    "hi": "Hindi", "hindi": "Hindi",
    "id": "Indonesian", "indonesian": "Indonesian",
    "vi": "Vietnamese", "vietnamese": "Vietnamese",
    "ms": "Malay", "malay": "Malay",
}

ALLOWED_TARGET_LANGS = sorted({v for v in LANG_CANON.values()})

BAD_OUTPUT_PATTERNS = [
    "```",
    "Here is the translation",
    "Here’s the translation",
    "Translation:",
    "Translated text:",
]

def _normalize_lang(name_or_code: Optional[str]) -> Optional[str]:
    if not name_or_code:
        return None
    key = name_or_code.strip().lower()
    return LANG_CANON.get(key, None)

def _detect_lang_name(text: str) -> Optional[str]:
    try:
        code = detect(text)
    except LangDetectException:
        return None
    code = code.lower()
    if "-" in code:
        code = code.split("-")[0]
    return _normalize_lang(code)

def _looks_like_explanation(s: str) -> bool:
    low = s.lower()
    return any(pat.lower() in low for pat in BAD_OUTPUT_PATTERNS)

class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TEXT_CHARS, description="Text to translate")
    target_lang: str = Field(..., min_length=1, description="Language to translate into (e.g., 'English')")
    source_lang: Optional[str] = Field(
        default=None,
        description="Optional source language (e.g., 'Thai'). If omitted, the model will infer it.",
    )

class TranslateResponse(BaseModel):
    translated_text: str

@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "Amp_Translator", "version": __version__}

@app.get("/version")
async def version():
    return {"version": __version__}

@app.post("/translate", response_model=TranslateResponse)
async def translate(body: TranslateRequest):
    target = _normalize_lang(body.target_lang)
    if not target or target not in ALLOWED_TARGET_LANGS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported target_lang. Allowed: {', '.join(ALLOWED_TARGET_LANGS)}",
        )

    if len(body.text) > MAX_TEXT_CHARS:
        raise HTTPException(status_code=413, detail=f"text too long (>{MAX_TEXT_CHARS} chars)")

    try:
        translated = await llama3_translate(
            text=body.text,
            target_lang=target,
            source_lang=_normalize_lang(body.source_lang),
        )
        if not translated:
            raise HTTPException(status_code=502, detail="Empty translation from model.")

        if _looks_like_explanation(translated):
            raise HTTPException(status_code=400, detail="Output rejected: contained explanation/formatting.")

        compact = ''.join(ch for ch in translated if not ch.isspace())
        if len(compact) >= 12:
            out_lang = _detect_lang_name(translated)
            if out_lang and out_lang != target:
                raise HTTPException(
                    status_code=400,
                    detail=f"Output language '{out_lang}' did not match target '{target}'.",
                )

        return TranslateResponse(translated_text=translated)

    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response else "N/A"
        preview = e.response.text[:500] if e.response else ""
        raise HTTPException(status_code=502, detail=f"Ollama returned {status}: {preview}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream model error: {e.__class__.__name__}")
