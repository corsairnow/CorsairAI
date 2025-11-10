import os, json, shutil
from typing import Dict, List
from ..core.config import KB_DIR
from chromadb import Client
from ..core.config import CHROMA_DIR
import chromadb




def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def kb_path(kb_id: str) -> str:
    return os.path.join(KB_DIR, kb_id)

def versions_dir(kb_id: str) -> str:
    return os.path.join(kb_path(kb_id), "versions")

def version_path(kb_id: str, kb_version_id: str) -> str:
    return os.path.join(versions_dir(kb_id), kb_version_id)

def _iso_to_ts(s: str) -> float:
    try:
        import datetime
        if s.endswith("Z"): s = s[:-1]
        return datetime.datetime.fromisoformat(s).timestamp()
    except Exception:
        return 0.0

def read_meta(kb_id: str, kb_version_id: str):
    try:
        with open(os.path.join(version_path(kb_id, kb_version_id), "meta.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def write_meta(kb_id: str, kb_version_id: str, meta: Dict):
    os.makedirs(version_path(kb_id, kb_version_id), exist_ok=True)
    with open(os.path.join(version_path(kb_id, kb_version_id), "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

def list_kbs() -> List[str]:
    if not os.path.isdir(KB_DIR):
        return []
    return [d for d in os.listdir(KB_DIR) if os.path.isdir(os.path.join(KB_DIR, d))]

def list_versions(kb_id: str) -> List[str]:
    vdir = versions_dir(kb_id)
    if not os.path.isdir(vdir): return []
    return sorted(os.listdir(vdir))

def active_version(kb_id: str) -> str:
    best = None
    best_ts = 0
    for vid in list_versions(kb_id):
        meta = read_meta(kb_id, vid)
        if not meta or meta.get("archived"): 
            continue
        ts = _iso_to_ts(meta.get("created_at",""))
        if ts > best_ts:
            best, best_ts = vid, ts
    return best

def soft_delete_kb(kb_id: str) -> bool:
    changed = False
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    coll =client.get_collection("chatbot")  # your collection name
    coll.delete(where={"kb_id": kb_id})

    for vid in list_versions(kb_id):
        meta = read_meta(kb_id, vid)
        if meta and not meta.get("archived"):
            meta["archived"] = True
            write_meta(kb_id, vid, meta)
            changed = True
    return changed

# def hard_delete_kb(kb_id: str) -> bool:
#     client = chromadb.PersistentClient(path=CHROMA_DIR)
#     coll =client.get_collection("chatbot")  # your collection name
#     coll.delete(where={"kb_id": kb_id})
#     kdir = kb_path(kb_id)
#     if os.path.isdir(kdir):
#         shutil.rmtree(kdir, ignore_errors=True)
#         return True
#     return False
