# backend/app.py
import os # os (Operating System) is a built-in Python module that lets your Python code interact with the computer's file system, folders, environment variables, and operating system features.
import json # json is a Python module used to convert Python data into JSON and JSON into Python data.
import uuid # uuid is a built-in Python module used to generate universally unique identifiers
import logging # logging is a built-in Python module that provides a standard way to record:errors,warnings,debug information,important events

from io import BytesIO
from threading import Lock # Lock is a thread synchronization tool in Python.It ensures that only one thread at a time can execute a piece of code.
from typing import List, Any, Dict

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# third-party libs used for extraction / embeddings
import openai
from pdfminer.high_level import extract_text as pdf_extract_text
import docx  # python-docx

# Load environment
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    # Don't crash at import time; we will raise on use, but log warning
    print("WARNING: OPENAI_API_KEY not set. Set it in backend/.env")

openai.api_key = OPENAI_API_KEY

# Config
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
#__file__ = full path of the current Python file (app.py)
# os.path.dirname(__file__) = This gives the folder location of app.py
#DATA_DIR = "C:\AI Repository\RAG-QA\backend\data"

DATA_FILE = os.path.join(DATA_DIR, "vectors.json")

#C:\AI Repository\RAG-QA\backend\data\vectors.json

ERROR_LOG = os.path.join(os.path.dirname(__file__), "error.log")

#C:\AI Repository\RAG-QA\backend\error.log

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800")) #This is the maximum number of characters in each text chunk
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))#Chunks overlap by 150 characters.
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
TOP_K = int(os.getenv("TOP_K", "1")) #Number of top similar chunks to retrieve during a query.

# Thread-safety for writes
_write_lock = Lock()

# Logging
logger = logging.getLogger("rag_backend")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(ERROR_LOG)
handler.setLevel(logging.ERROR)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# FastAPI app
app = FastAPI(title="Simple Local RAG Backend")#This sets the title of your API documentation.http://localhost:8000/docs
#FastAPI is a Python framework used to create:
#REST APIs
#Backend servers
#Endpoints (routes) like /upload, /query, /health
#It is very fast, supports async operations, and automatically generates documentation.

#This code enables CORS support in your FastAPI backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------- Utilities: data file safe handling -----------------
def ensure_data_file() -> None:
    """Ensure data directory and JSON file exist and contain a valid JSON list."""
    try:
        if not os.path.exists(DATA_DIR):#If the folder backend/data/ does not exist → create it
            #exist_ok=True prevents errors if folder already exists
            os.makedirs(DATA_DIR, exist_ok=True)
        # If file doesn't exist -> create empty list
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
            return

        # If file exists but is empty or invalid -> backup & rewrite
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            if not content.strip():
                raise ValueError("empty file")
            parsed = json.loads(content)
            if not isinstance(parsed, list):
                raise ValueError("file not list")
    except Exception:
        try:
            # attempt to backup original file
            bak = DATA_FILE + ".bak"
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "r", encoding="utf-8") as orig, open(bak, "w", encoding="utf-8") as ob:
                    ob.write(orig.read())
        except Exception:
            pass
        # create fresh empty list
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def load_local_vectors() -> List[Dict[str, Any]]:
    ensure_data_file()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                return []
            return data
    except json.JSONDecodeError:
        # attempt to recover
        with _write_lock:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
        return []
    except Exception as e:
        logger.error(f"load_local_vectors error: {e}")
        return []


def save_local_vectors(data: List[Dict[str, Any]]) -> None:
    # atomic write using tmp file and replace
    with _write_lock:
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DATA_FILE)


# ----------------- Text extraction -----------------
def extract_text_from_upload(upload: UploadFile) -> str:
    """Support .txt, .pdf, .docx. Raise HTTPException on unsupported types."""
    name = (upload.filename or "").lower()
    raw = upload.file.read()
    upload.file.seek(0)
    if name.endswith(".txt"):
        try:
            return raw.decode("utf-8", errors="ignore")
        except Exception:
            return raw.decode("latin-1", errors="ignore")
    if name.endswith(".pdf"):
        try:
            return pdf_extract_text(BytesIO(raw))
        except Exception as e:
            logger.error(f"PDF extract error for {upload.filename}: {e}")
            raise HTTPException(status_code=400, detail=f"PDF extract failed: {upload.filename}")
    if name.endswith(".docx"):
        try:
            doc = docx.Document(BytesIO(raw))
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            logger.error(f"DOCX extract error for {upload.filename}: {e}")
            raise HTTPException(status_code=400, detail=f"DOCX extract failed: {upload.filename}")
    raise HTTPException(status_code=400, detail=f"Unsupported file type: {upload.filename}")


# ----------------- Chunking -----------------
def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")
    text = text.strip()
    if not text:
        return []
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk.strip())
        start = end - overlap
    return [c for c in chunks if c]


# ----------------- Embeddings -----------------
def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Call OpenAI Embeddings API. Raises exception if API key missing."""
    if not openai.api_key:
        raise RuntimeError("OPENAI_API_KEY not configured. Set it in backend/.env")
    # OpenAI supports batching by passing list of inputs
    resp = openai.Embedding.create(input=texts, model=EMBEDDING_MODEL)
    embeddings = [d["embedding"] for d in resp["data"]]
    return embeddings


# ----------------- Similarity utilities -----------------
def dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def norm(a: List[float]) -> float:
    import math
    return math.sqrt(sum(x * x for x in a))


def cosine_similarity(a: List[float], b: List[float]) -> float:
    na = norm(a)
    nb = norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return dot(a, b) / (na * nb)


# ----------------- Endpoints -----------------
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # log full traceback for server-side debugging
    logger.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.post("/api/admin/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Upload multiple files as 'files' form fields.
    Example form keys:
      files: <file1>
      files: <file2>
    Returns number of added chunks.
    """
    total_added = 0
    try:
        if not files:
            return {"status": "error", "detail": "No files provided."}

        # load current vectors
        all_vectors = load_local_vectors()

        for upload in files:
            try:
                text = extract_text_from_upload(upload)
            except HTTPException as he:
                # skip unsupported/broken file but continue other files
                logger.error(f"Skipping file {upload.filename}: {he.detail}")
                continue

            chunks = chunk_text(text)
            if not chunks:
                continue

            # get embeddings in batches (OpenAI can handle multiple inputs)
            try:
                embeddings = get_embeddings(chunks)
            except Exception as e:
                logger.exception("Embedding generation failed")
                raise HTTPException(status_code=500, detail=f"Embedding error: {e}")

            # upsert chunk items to local list
            for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                item = {
                    "id": str(uuid.uuid4()),
                    "filename": upload.filename,
                    "chunk_index": idx,
                    "text": chunk,
                    "embedding": emb,
                }
                all_vectors.append(item)
                total_added += 1

        # persist to disk
        save_local_vectors(all_vectors)
        return {"status": "ok", "added_chunks": total_added}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Upload failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/user/query")
async def query(payload: Dict[str, Any]):
    """
    Body: { "q": "<question text>", "k": optional int }
    Returns: best-matching chunks and an aggregated 'answer' (concatenation).
    """
    try:
        q = payload.get("q") if isinstance(payload, dict) else None
        if not q or not isinstance(q, str):
            raise HTTPException(status_code=400, detail="Missing 'q' in request body")

        k = int(payload.get("k", TOP_K)) if isinstance(payload, dict) else TOP_K
        if k <= 0:
            k = TOP_K

        # embed the question
        try:
            q_emb = get_embeddings([q])[0]
        except Exception as e:
            logger.exception("Failed to embed query")
            raise HTTPException(status_code=500, detail=f"Embedding error: {e}")

        # load vectors
        data = load_local_vectors()
        if not data:
            return {"answer": "", "sources": []}

        # compute similarity scores
        scored = []
        for item in data:
            emb = item.get("embedding")
            if not emb:
                continue
            try:
                score = cosine_similarity(q_emb, emb)
            except Exception:
                score = 0.0
            scored.append((score, item))

        # sort and take top k
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:k]

        # build answer by concatenating top chunks (simple)
        answer = "\n\n---\n".join([it["text"] for _, it in top])

        sources = [
            {
                "filename": it.get("filename"),
                "chunk_index": it.get("chunk_index"),
                "score": float(score),
                "text": it.get("text")[:400],
            }
            for score, it in top
        ]

        return {"answer": answer, "sources": sources}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Query failed")
        raise HTTPException(status_code=500, detail=str(exc))
