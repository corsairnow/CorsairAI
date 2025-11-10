import os
from dotenv import load_dotenv

load_dotenv()

VERSION = "1.0.0"

DATA_ROOT = os.getenv("DATA_ROOT", "./root")
CHROMA_DIR = os.getenv("CHROMA_DIR", os.path.join(DATA_ROOT, "chroma"))
UPLOADS_DIR = os.path.join(DATA_ROOT, "uploads")
KB_DIR = os.path.join(DATA_ROOT, "kb")
CHATS_DIR = os.path.join(DATA_ROOT, "chats")
LOCKS_DIR = os.path.join(DATA_ROOT, "locks")
LOGS_DIR = os.path.join(DATA_ROOT, "logs")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "mxbai-embed-large")
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3:8b")

# Chunking defaults
MAX_CHARS = int(os.getenv("MAX_CHARS", "2200"))
OVERLAP_CHARS = int(os.getenv("OVERLAP_CHARS", "220"))

RETRIEVAL_K_PER_KB = int(os.getenv("RETRIEVAL_K_PER_KB", "8"))
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.20"))








