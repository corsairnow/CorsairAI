# app/main.py
import os, json, time
from typing import List, Dict
from fastapi import FastAPI, HTTPException, Request,UploadFile,File,Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import VERSION, UPLOADS_DIR, KB_DIR, CHROMA_DIR, RETRIEVAL_K_PER_KB, CONFIDENCE_THRESHOLD
from app.core.models import *
from app.kb.ingest import ingest_files
from app.kb.store import list_kbs, list_versions, read_meta, active_version, soft_delete_kb, version_path
from app.chat.store import create_chat, get_chat, append_message, get_messages, ensure_db
from app.core.ollama import embed_texts, chat_complete
import chromadb
import shutil
from nltk.corpus import wordnet  # Import wordnet to get synonyms
# import nltk
# import spacy
# from scipy.spatial.distance import cosine


app = FastAPI(title="AMP_Support_Bot", version=VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dev helper: return JSON for any unhandled 500 so jq can parse it
@app.exception_handler(Exception)
async def unhandled_exc(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": {"type": exc.__class__.__name__, "detail": str(exc)}},
    )

START_TIME = time.time()

def ensure_dirs():
    for d in [UPLOADS_DIR, KB_DIR, CHROMA_DIR]:
        os.makedirs(d, exist_ok=True)
ensure_dirs()
ensure_db()

@app.get("/healthz")
async def healthz():
    return {"status": "ok", "uptime_s": round(time.time()-START_TIME, 2)}

@app.get("/version")
async def version():
    return {"version": VERSION}

# @app.post("/kb/ingest")
# @app.post("/knowledge-base/document/add")
# async def kb_ingest(body: KBIngestBody):
#     lock_path = os.path.join(os.path.dirname(CHROMA_DIR), "locks", "ingest.lock")
#     os.makedirs(os.path.dirname(lock_path), exist_ok=True)
#     if os.path.exists(lock_path):
#         raise HTTPException(status_code=409, detail="Another ingest is running")
#     open(lock_path, "w").write(str(time.time()))
#     try:
#         out = await ingest_folder(body.KB_name)
#         return out
#     except FileNotFoundError as e:
#         raise HTTPException(status_code=404, detail=str(e))
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     finally:
#         try:
#             os.remove(lock_path)
#         except FileNotFoundError:
#             pass

@app.post("/knowledge-base/document/add")
async def kb_ingest(folder_name: str = Form(...), files: List[UploadFile] = File(...)):
    # folder_name = body.folder_name  # Folder name passed in the request
    print(folder_name)
    # print(files.filenames)
    # Locking mechanism to avoid concurrent ingest operations
    lock_path = os.path.join(os.path.dirname(CHROMA_DIR), "locks", "ingest.lock")
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    
    if os.path.exists(lock_path):
        raise HTTPException(status_code=409, detail="Another ingest is running")
    
    open(lock_path, "w").write(str(time.time()))  # Create a lock file

    try:
        # Step 1: Create the folder to save files
        save_path = os.path.join(UPLOADS_DIR, folder_name)
        print(f"Saving files to: {save_path}")
        os.makedirs(save_path, exist_ok=True)

        saved_files = []  # List to store saved file paths

        # Step 2: Save files from the request to the specified folder
        for file in files:
            file_path = os.path.join(save_path, file.filename)  # Full path to save the file
            
            # Save the file content to disk
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)  # Write the file content
            saved_files.append(file_path)  # Add the file path to the list
            print(f"File saved: {file_path}")
        
        # Step 3: Process the saved files (implement your ingest function)
        out = await ingest_files(saved_files)  # Assuming ingest_files is defined elsewhere

        return {"message": "Files uploaded and ingested successfully", "result": out}  # Return the result of ingestion

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Value error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    finally:
        # Cleanup the lock file
        try:
            os.remove(lock_path)
        except FileNotFoundError:
            pass

# @app.get("/kb")
@app.get("/knowledge-base/list")
async def kb_list():
    items = []
    for kid in list_kbs():
        av = active_version(kid)
        files=chunks=0
        created=None
        if av:
            meta = read_meta(kid, av)
            files = meta.get("source_stats",{}).get("files",0)
            chunks = meta.get("chunks",0)
            created = meta.get("created_at")
        size_bytes = 0
        vdir = os.path.join(KB_DIR, kid, "versions")
        for root, _, files_list in os.walk(vdir):
            for fn in files_list:
                try:
                    size_bytes += os.path.getsize(os.path.join(root, fn))
                except FileNotFoundError:
                    pass
        items.append({
            "kb_id": kid,
            "active_version": av,
            "files": files,
            "chunks": chunks,
            "created_at": created,
            "size_mb": round(size_bytes/1_000_000, 3),
        })
    return items

# @app.get("/kb/{kb_id}")
@app.get("/knowledge-base/list-by-id/{kb_id}")
async def kb_detail(kb_id: str):
    vers = list_versions(kb_id)
    if not vers:
        raise HTTPException(status_code=404, detail="KB not found")
    versions = []
    for v in vers:
        meta = read_meta(kb_id, v)
        if not meta: 
            continue
        versions.append({
            "kb_version_id": meta["kb_version_id"],
            "created_at": meta["created_at"],
            "files": meta.get("source_stats",{}).get("files",0),
            "chunks": meta.get("chunks",0),
            "embedding": meta.get("embedding",{}).get("model",""),
            "index_engine": meta.get("index",{}).get("engine","chroma"),
            # "tags": meta.get("tags",[])
        })
    av = active_version(kb_id)
    sample = []
    if av:
        src_dir = os.path.join(version_path(kb_id, av), "source")
        for root, _, files in os.walk(src_dir):
            for fn in files:
                if fn.lower().endswith(".md"):
                    rel = os.path.relpath(os.path.join(root, fn), src_dir)
                    sample.append({"path": rel})
                    if len(sample)>=5:
                        break
            if len(sample)>=5: break
    return {"kb_id": kb_id, "versions": versions, "active_version": av, "sample_docs": sample}

# @app.delete("/kb/{kb_id}")
@app.post("/knowledge-base/delete/{kb_id}")
# async def kb_delete(kb_id: str, force: bool=False):
async def kb_delete(kb_id: str):
    if not list_versions(kb_id):
        raise HTTPException(status_code=404, detail="KB not found")
   
    changed = soft_delete_kb(kb_id)
    return {"kb_id": kb_id, "deleted": True, "mode": "soft", "changed": changed}
    # else:
    #     ok = hard_delete_kb(kb_id)
    #     return {"kb_id": kb_id, "deleted": ok, "mode": "hard"}

# from fastapi import Body - further use 

# @app.delete("/kb/{kb_id}")
# async def kb_delete(kb_id: str, body: Optional[TicketDeleteBody] = Body(None)):
#     if kb_id == "tickets":
#         if not body or not body.ticket_ids:
#             raise HTTPException(status_code=400, detail="ticket_ids required for deleting tickets")
        
#         # Delete only these tickets from vector DB
#         client = chromadb.PersistentClient(path=CHROMA_DIR)
#         coll = client.get_collection("chatbot")
#         coll.delete(where={"kb_id": "tickets", "ticket_id": {"$in": body.ticket_ids}})
        
#         return {"kb_id": kb_id, "deleted_tickets": body.ticket_ids}
    
#     # For document KBs
#     if not list_versions(kb_id):
#         raise HTTPException(status_code=404, detail="KB not found")
    
#     changed = soft_delete_kb(kb_id)
#     return {"kb_id": kb_id, "deleted": True, "mode": "soft", "changed": changed}

# def _resolve_bindings(kb_ids: List[str]) -> List[Dict[str,str]]:
#     bindings = []
#     for kid in kb_ids:
#         av = active_version(kid)
#         if not av:
#             raise HTTPException(status_code=404, detail=f"No active version for KB '{kid}'")
#         bindings.append({"kb_id": kid, "kb_version_id": av})
#     return bindings

async def _retrieve( query: str, k_per_kb: int):
    print(f"235 {CHROMA_DIR}")
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    print("237")

    print(client.list_collections())


    print("242")

    q_emb = (await embed_texts([query]))[0]
    print("245")

    pooled = []
    # for b in kb_bindings:
        # name = f"{b['kb_id']}__{b['kb_version_id']}"
    name="chatbot"
    try:
        print("252")

        coll = client.get_collection(name)
        print("255")

    except Exception as e:
        print("254")
        print(e)
        pass
    # Chroma 0.5.x: do NOT include "ids" here
    # --- Vector search ---
    res = coll.query(
        query_embeddings=[q_emb],
        n_results=k_per_kb,
        include=["metadatas", "documents", "distances"]
    )
    print("264")

    # Safe row count regardless of ids presence
    row_count = len(res["documents"][0]) if "documents" in res else 0
    print("268")

    for i in range(row_count):
        pooled.append({
            "id": (res.get("ids", [[""]])[0][i] if "ids" in res else ""),
            "doc": res["metadatas"][0][i].get("doc",""),
            "title": res["metadatas"][0][i].get("title",""),
            "text": res["documents"][0][i],
            "score": 1.0 - float(res["distances"][0][i])
        })

        #--- Keyword search ---
        all_docs = coll.get(include=["metadatas", "documents"])
        for doc_text, meta in zip(all_docs["documents"], all_docs["metadatas"]):
            if query.lower() in doc_text.lower() or query.lower() in meta.get("title","").lower():
                pooled.append({
                    "id": meta.get("doc","") + "_kw",
                    "doc": meta.get("doc",""),
                    "title": meta.get("title",""),
                    "text": doc_text,
                    "score": 0.8,   # keyword match score, lower than vector
                    "source": "keyword"
                })
    # --- Deduplicate and sort ---
    pooled.sort(key=lambda x: x["score"], reverse=True)
    top, seen = [], set()
    for item in pooled:
        key = item["doc"]
        if key in seen:
            continue
        top.append(item)
        seen.add(key)
        if len(top) >= max(12, k_per_kb):
            break
    print("302")
    return top

def _build_prompt(query: str, ctx_items: List[Dict]) -> str:
    lines = []
    for i, it in enumerate(ctx_items, start=1):
        snippet = it["text"][:800]
        lines.append(f"[{i}] {it['doc']} — {it['title']}\n{snippet}")
    ctx = "\n\n".join(lines) if lines else "(no relevant context found)"
    return f"""
    Context:
    {ctx}

    User Question:
    {query}

    Instructions:
    **EXCEPTION FOR GREETINGS: If the user sends a greeting (like "hi", "hello", "hey", "good morning", etc.) or casual conversational message that doesn't require context information, respond briefly and warmly (e.g., "Hello! How can I help you today?").**
    -Strictly don't give other answer when user greet give them greet and ask just "how can i help you?"
    -Answer the user question ONLY using the information in the Context above.
    -If the Context does not contain enough information, clearly say:
     "I do not have enough information to answer that."
    -Keep the answer concise, clear, and friendly, suitable for a user reading it directly.
    -Do NOT include citations or brackets in the answer — it should read naturally.
    -Do not add any information from outside the Context.

    """
    # return f"""Context:
    # {ctx}
    # User question:
    # {query}
    # Instructions:
    # - Answer ONLY from the Context above.
    # - If the Context is insufficient, say you do not have enough information in the knowledge base.
    # - Keep a concise, friendly support tone.
    # - Cite sources in brackets like [1], [2] aligned to the items in Context.
    # """

def _extract_citations(ctx_items: List[Dict], text: str):
    import re
    idxs = set(int(m.group(1)) for m in re.finditer(r'\[(\d+)\]', text) if m.group(1).isdigit())
    if not idxs:
        idxs = set(range(1, min(4, len(ctx_items))+1))
    out = []
    for i in sorted(idxs):
        if 1 <= i <= len(ctx_items):
            it = ctx_items[i-1]
            out.append({"doc": it["doc"], "snippet": it["text"][:240], "score": float(it["score"])})
    return out
# 

def get_synonyms(word):
    synonyms = set()
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            synonyms.add(lemma.name())  # Add the synonym to the set
    return synonyms

def detect_dissatisfaction(message: str) -> bool:
    dissatisfaction_keywords = [
        "raise ticket", "contact support", "need support", "connect me with agent",
        "talk to agent", "open ticket", "technical issue", "customer care", "help me",
        "this isn't helpful", "doesn't work", "not what I asked", "I'm confused", 
        "not what I needed", "can't get it to work", "this is wrong","raise ticket",
        "contact support",
        "need support",
        "connect me with agent",
        "talk to agent",
        "open ticket",
        "technical issue",
        "customer care",
        "help me",
        "this isn't helpful",
        "doesn't work",
        "not what I asked",
        "I'm confused",
        "not what I needed",
        "help me",
        "can't get it to work",
        "this is wrong"
    ]
    
    # Additional keywords for more flexible matching
    additional_keywords = ["ticket", "support", "help", "assist", "problem", "issue", "agent", "customer service", "contact"]

    message_lower = message.lower()

    # First, check if any dissatisfaction keyword is in the user's message
    for word in dissatisfaction_keywords:
        if word in message_lower:
            return True
    
    # Second, check for additional related words (using basic keyword matching)
    if any(keyword in message_lower for keyword in additional_keywords):
        return True

    # If no dissatisfaction keyword or related keyword is found, return False
    return False
# Convert dissatisfaction-related phrases to vectors
    # dissatisfaction_vectors = [nlp(keyword).vector for keyword in dissatisfaction_keywords]
    # message_vector = nlp(message).vector  # Get vector for the user's message
    # max_similarity = 0  # Track the maximum similarity score

    # # Calculate similarity with each predefined dissatisfaction phrase
    # for vector in dissatisfaction_vectors:
    #     similarity = 1 - cosine(message_vector, vector)
    #     max_similarity = max(max_similarity, similarity)  # Update max similarity
        
    #     # If the similarity surpasses the threshold, break early for better performance
    #     if max_similarity > 0.85:  # Adjust the threshold as needed (e.g., 0.85)
    #         return True

    # # If no similarity exceeds the threshold, return False
    # return False
    # Calculate similarity with each predefined dissatisfaction phrase
    # for vector in dissatisfaction_vectors:
    #     similarity = 1 - cosine(message_vector, vector)
    #     if similarity > 0.7:  # You can adjust the threshold (0.7 in this case)
    #         return True
    
    # return False
    # Alternatively, use OpenAI to detect frustration/satisfaction using sentiment or keywords
    # response = openai.Completion.create(
    #     model="text-davinci-003",
    #     prompt=f"Detect if the following message expresses dissatisfaction or frustration: '{message}'",
    #     max_tokens=10
    # )
    
    # result = response.choices[0].text.strip().lower()
    # return "yes" in result

@app.post("/chat/start", response_model=ChatReply)
async def chat_start(body: ChatStartBody):

    # bindings = _resolve_bindings(body.kb_ids)
    # chat_id = create_chat(bindings)
    chat_id = create_chat()

    append_message(chat_id, "user", body.message)
    print("line no 427")
    ctx_items = await _retrieve(body.message, RETRIEVAL_K_PER_KB)
    print("line no 428")
    conf = max([x["score"] for x in ctx_items], default=0.0)
    prompt = _build_prompt(body.message, ctx_items)
    start = time.time()
    text = await chat_complete(prompt, stream=False)
    latency_ms = int((time.time()-start)*1000)
    abstained = (conf < CONFIDENCE_THRESHOLD) or ("do not have enough" in text.lower())
    citations = _extract_citations(ctx_items, text)
    append_message(chat_id, "assistant", text)
    flag=detect_dissatisfaction(body.message)
    # return ChatReply(chat_id=chat_id, kb_bindings=bindings, reply=text, citations=citations, abstained=bool(abstained), latency_ms=latency_ms)
    return ChatReply(chat_id=chat_id, reply=text, citations=citations, abstained=bool(abstained), latency_ms=latency_ms,is_raise_ticket=flag)



@app.post("/chat/reply", response_model=ChatReply)
async def chat_reply(body: ChatReplyBody):
    chat = get_chat(body.chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Unknown chat_id")
    # bindings = chat["kb_bindings"]
    append_message(body.chat_id, "user", body.message)
    ctx_items = await _retrieve( body.message, RETRIEVAL_K_PER_KB)
    conf = max([x["score"] for x in ctx_items], default=0.0)
    prompt = _build_prompt(body.message, ctx_items)
    start = time.time()
    text = await chat_complete(prompt, stream=False)
    latency_ms = int((time.time()-start)*1000)
    abstained = (conf < CONFIDENCE_THRESHOLD) or ("do not have enough" in text.lower())
    citations = _extract_citations(ctx_items, text)
    append_message(body.chat_id, "assistant", text)
    flag=detect_dissatisfaction(body.message)
    return ChatReply(chat_id=body.chat_id, reply=text, citations=citations, abstained=bool(abstained), latency_ms=latency_ms,is_raise_ticket=flag)
    # return ChatReply(chat_id=body.chat_id, kb_bindings=bindings, reply=text, citations=citations, abstained=bool(abstained), latency_ms=latency_ms)



@app.get("/chat/{chat_id}")
async def chat_get(chat_id: str):
    chat = get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Unknown chat_id")
    msgs = [{"role": r, "text": t, "ts": ts} for (r, t, ts) in get_messages(chat_id, limit=50)]
    return {"chat_id": chat_id, "messages": msgs}
    # return {"chat_id": chat_id, "kb_bindings": chat["kb_bindings"], "messages": msgs, "rolling_summary": chat["rolling_summary"]}

