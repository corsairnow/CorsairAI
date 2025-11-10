import os, json, time, hashlib
from typing import Dict
from ..core.config import UPLOADS_DIR, MAX_CHARS, OVERLAP_CHARS, EMBED_MODEL, CHROMA_DIR
from ..utils.text import read_docx,read_pdf,read_markdown, normalize_markdown, split_heading_aware, file_digest,slugify_filename
from ..core.ollama import embed_texts
from .store import ensure_dir, version_path, write_meta
import chromadb


# def compute_manifest(upload_folder: str) -> Dict:
#     files = []
#     total_bytes = 0
#     for root, _, fnames in os.walk(upload_folder):
#         for fn in fnames:
#             if not fn.lower().endswith((".md", ".pdf", ".docx")):
#                 continue
#             full = os.path.join(root, fn)
#             rel = os.path.relpath(full, upload_folder)
#             digest = file_digest(full)
#             size = os.path.getsize(full)
#             total_bytes += size
#             files.append({"path": rel, "digest": digest, "size": size})
#     files.sort(key=lambda x: x["path"])
#     src_manifest = hashlib.blake2b(json.dumps(files).encode("utf-8"), digest_size=16).hexdigest()
#     return {"files": files, "bytes": total_bytes, "manifest": src_manifest}

def compute_file_manifest(file_path: str) -> Dict:
    """
    Compute the manifest for a single file instead of a folder.
    Returns a dict containing file info, total bytes, and a manifest hash.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not file_path.lower().endswith((".md", ".pdf", ".docx")):
        # Skip unsupported file types
        return {"files": [], "bytes": 0, "manifest": ""}
    
    size = os.path.getsize(file_path)
    # Compute digest of file content
    with open(file_path, "rb") as f:
        content = f.read()
        digest = hashlib.blake2b(content, digest_size=16).hexdigest()
    
    file_name = os.path.basename(file_path)
    files = [{"path": file_name, "digest": digest, "size": size}]
    
    # Manifest hash for this single file
    src_manifest = hashlib.blake2b(json.dumps(files).encode("utf-8"), digest_size=16).hexdigest()
    
    return {"files": files, "bytes": size, "manifest": src_manifest}


def read_file_by_type(file_path: str) -> str:
    """Route file reading based on extension."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".md":
        return read_markdown(file_path)
    elif ext == ".pdf":
        return read_pdf(file_path)
    elif ext == ".docx":
        return read_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    

# async def ingest_folder(folder_name: str) -> Dict:
#     upload_folder = os.path.join(UPLOADS_DIR, folder_name)
#     if not os.path.isdir(upload_folder):
#         raise FileNotFoundError(f"uploads/{folder_name} not found")
#     # Use folder name almost verbatim (see slugify comment)
#     kb_id = slugify(folder_name)

#     manifest = compute_manifest(upload_folder)
#     if not manifest["files"]:
#         raise ValueError("No .md/pdf/docx files found in the folder")

#     ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
#     ver_digest = hashlib.blake2b(
#         (manifest["manifest"] + f"|max{MAX_CHARS}|ov{OVERLAP_CHARS}|embed:{EMBED_MODEL}")
#         .encode("utf-8"), digest_size=6
#     ).hexdigest()
#     kb_version_id = f"{ts[:10]}--b3_{ver_digest}"

#     src_dir = os.path.join(version_path(kb_id, kb_version_id), "source")
#     ensure_dir(src_dir)

#     documents = []
#     for f in manifest["files"]:
#         in_path = os.path.join(upload_folder, f["path"])
#         raw_text = read_file_by_type(in_path)
#         norm = normalize_markdown(raw_text)
#         out_path = os.path.join(src_dir, f["path"])
#         os.makedirs(os.path.dirname(out_path), exist_ok=True)
#         with open(out_path, "w", encoding="utf-8") as w:
#             w.write(norm)

#         chunks = split_heading_aware(norm, MAX_CHARS, OVERLAP_CHARS)
#         for i, ch in enumerate(chunks):
#             text = (ch["text"] or "").strip()
#             if not text:
#                 continue
#             documents.append({
#                 "id": f"{f['path']}::chunk{i}",
#                 "doc": f["path"],
#                 "title": ch["title"],
#                 "text": text
#             })

#     if not documents:
#         raise ValueError("No ingestible text chunks found (all files were empty/headers-only).")
#     # print(CHROMA_DIR)
#     client = chromadb.PersistentClient(path=CHROMA_DIR)
#     # coll_name = f"{kb_id}__{kb_version_id}"
#     coll_name= "chatbot"
#     try:
#         coll = client.get_collection(name=coll_name)
#         # coll.upsert(
#         #     ids=ids,
#         #     embeddings=embeddings,
#         #     documents=texts,
#         #     metadatas=[
#         #         {"kb_id": kb_id, "version": kb_version_id, "doc": d["doc"]}
#         #         for d in documents
#         #     ])
#         # client.delete_collection(coll_name)
#     except Exception:
#         coll = client.create_collection(name=coll_name, metadata={"kb_id": kb_id, "kb_version_id": kb_version_id})
    
#     batch = 64
#     ids, embeddings, metadatas, texts = [], [], [], []
#     for i in range(0, len(documents), batch):
#         batch_docs = [d for d in documents[i:i+batch] if d["text"].strip()]
#         if not batch_docs:
#             continue
#         btexts = [d["text"] for d in batch_docs]
#         embs = await embed_texts(btexts)
#         cleaned = [(d, e) for d, e in zip(batch_docs, embs) if isinstance(e, list) and len(e) > 0]
#         for d, e in cleaned:
#             ids.append(d["id"])
#             embeddings.append(e)
#             metadatas.append({"doc": d["doc"], "title": d["title"]})
#             texts.append(d["text"])

#     if not ids:
#         raise ValueError("Embedding failed or returned empty vectors. Check your Ollama embed model.")

#     # coll.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=texts)
#     coll.upsert(
#             ids=ids,
#             embeddings=embeddings,
#             documents=texts,
#             metadatas=[
#                 {"kb_id": kb_id, "version": kb_version_id, "doc": d["doc"]}
#                 for d in documents
#             ])

#     meta = {
#         "kb_id": kb_id,
#         "kb_version_id": kb_version_id,
#         "created_at": ts,
#         "source_stats": {"files": len(manifest["files"]), "bytes": manifest["bytes"]},
#         "chunking": {"mode": "heading_aware", "max_chars": MAX_CHARS, "overlap_chars": OVERLAP_CHARS},
#         "embedding": {"model": EMBED_MODEL},
#         "index": {"engine": "chroma"},
#         "chunks": len(ids),
#         "hashes": {"source_manifest": manifest["manifest"], "full_version": ver_digest},
#         "tags": []
#     }
    
#     write_meta(kb_id, kb_version_id, meta)
#     return {
#         "kb_id": kb_id,
#         "kb_version_id": kb_version_id,
#         "files": len(manifest["files"]),
#         "chunks": len(ids),
#         "created_at": ts,
#         "embedding": EMBED_MODEL,
#         "index_engine": "chroma"
#     }


async def ingest_files(file_paths: list) -> Dict:
    all_kb_data = []  # List to store each file's KB metadata
    print("here")
    for file_path in file_paths:
        print("here0")
        documents = []  # Reset documents per file
        file_name = os.path.basename(file_path)
        print(file_name)
        kb_id = slugify_filename(file_name)
        print("here1")
        # Step 1: Compute manifest for this file
        manifest = compute_file_manifest(file_path)
        if not manifest["files"]:
            raise ValueError(f"No valid files found for {file_name}")

        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        ver_digest = hashlib.blake2b(
            (manifest["manifest"] + f"|max{MAX_CHARS}|ov{OVERLAP_CHARS}|embed:{EMBED_MODEL}")
            .encode("utf-8"), digest_size=6
        ).hexdigest()
        kb_version_id = f"{ts[:10]}--b3_{ver_digest}"

        # Step 2: Set up source directory
        src_dir = os.path.join(version_path(kb_id, kb_version_id), "source")
        ensure_dir(src_dir)

        # Step 3: Read and normalize file content
        raw_text = read_file_by_type(file_path)
        norm = normalize_markdown(raw_text)

        # Save normalized content
        out_path = os.path.join(src_dir, file_name)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as w:
            w.write(norm)

        # Step 4: Chunk text
        chunks = split_heading_aware(norm, MAX_CHARS, OVERLAP_CHARS)
        for i, ch in enumerate(chunks):
            text = (ch["text"] or "").strip()
            if not text:
                continue
            documents.append({
                "id": f"{file_name}::chunk{i}",
                "doc": file_name,
                "title": ch["title"],
                "text": text
            })

        if not documents:
            raise ValueError(f"No ingestible text chunks found for {file_name} (all files were empty/headers-only).")

        # Step 5: Chroma DB
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        coll_name = "chatbot"
        try:
            coll = client.get_collection(name=coll_name)
        except Exception:
            coll = client.create_collection(name=coll_name, metadata={"kb_id": kb_id, "kb_version_id": kb_version_id})

        # Step 6: Batch embeddings
        batch = 64
        ids, embeddings, metadatas, texts = [], [], [], []
        for i in range(0, len(documents), batch):
            batch_docs = [d for d in documents[i:i+batch] if d["text"].strip()]
            if not batch_docs:
                continue
            btexts = [d["text"] for d in batch_docs]
            embs = await embed_texts(btexts)
            cleaned = [(d, e) for d, e in zip(batch_docs, embs) if isinstance(e, list) and len(e) > 0]
            for d, e in cleaned:
                ids.append(d["id"])
                embeddings.append(e)
                metadatas.append({"doc": d["doc"], "title": d["title"]})
                texts.append(d["text"])

        if not ids:
            raise ValueError("Embedding failed or returned empty vectors. Check your Ollama embed model.")

        # Step 7: Upsert into Chroma
        coll.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=[{"kb_id": kb_id, "version": kb_version_id, "doc": d["doc"]} for d in documents]
        )

        # Step 8: Write metadata
        meta = {
            "kb_id": kb_id,
            "kb_version_id": kb_version_id,
            "created_at": ts,
            "source_stats": {"files": len(manifest["files"]), "bytes": manifest["bytes"]},
            "chunking": {"mode": "heading_aware", "max_chars": MAX_CHARS, "overlap_chars": OVERLAP_CHARS},
            "embedding": {"model": EMBED_MODEL},
            "index": {"engine": "chroma"},
            "chunks": len(ids),
            "hashes": {"source_manifest": manifest["manifest"], "full_version": ver_digest},
            "tags": []
        }
        write_meta(kb_id, kb_version_id, meta)

        # Step 9: Append to all KBs list
        all_kb_data.append({
            "kb_id": kb_id,
            "kb_version_id": kb_version_id,
            "files": 1,
            "chunks": len(ids),
            "created_at": ts,
            "embedding": EMBED_MODEL,
            "index_engine": "chroma",
            # "success": true
        })

    # Step 10: Return all KBs
    return {"kb_ids": all_kb_data}
