from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from fastapi import  UploadFile

class KBIngestBody(BaseModel):
    folder_name: str
    # file_names: List[UploadFile]

class ChatStartBody(BaseModel):
    # kb_ids: List[str] = Field(min_length=1)
    message: str
    # language: str = "en"
    # stream: bool = False

class ChatReplyBody(BaseModel):
    chat_id: str
    message: str
    # stream: bool = False

class Citation(BaseModel):
    doc: str
    snippet: str
    score: float

class ChatReply(BaseModel):
    chat_id: str
    # kb_bindings: List[Dict[str, str]]
    reply: str
    citations: List[Citation]
    abstained: bool
    latency_ms: int
    is_raise_ticket: bool  # New field added to flag whether a ticket is raised





