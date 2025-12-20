# backend/app.py

import os# os (Operating System) is a built-in Python module that lets your Python code interact with the computer's file system, folders, environment variables, and operating system features.
import json # json is a Python module used to convert Python data into JSON and JSON into Python data.
import uuid # uuid is a built-in Python module used to generate universally unique identifiers
import logging # logging is a built-in Python module that provides a standard way to record:errors,warnings,debug information,important events

import math
from io import BytesIO
from threading import Lock # Lock is a thread synchronization tool in Python.It ensures that only one thread at a time can execute a piece of code.
from typing import List, Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
# third-party libs used for extraction / embeddings
import openai
from pdfminer.high_level import extract_text as pdf_extract_text
import docx  # python-docx

# -------------------- ENV SETUP --------------------
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY not set")

openai.api_key = OPENAI_API_KEY

# -------------------- CONFIG --------------------
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "vectors.json")
ERROR_LOG = os.path.join(BASE_DIR, "error.log")

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")
TOP_K = int(os.getenv("TOP_K", "3"))

_write_lock = Lock()

# -------------------- LOGGING --------------------
logger = logging.getLogger("rag_backend")
logger.setLevel(logging.INFO)

handler = logging.FileHandler(ERROR_LOG)
handler.setLevel(logging.ERROR)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# -------------------- FASTAPI APP --------------------
app = FastAPI(title="Local RAG Backend (Human-like Answers)")
#FastAPI is a Python framework used to create:
#REST APIs
#Backend servers
#Endpoints (routes) like /upload, /query, /health
#It is very fast, supports async operations, and automatically generates documentation.

#This code enables CORS support in your FastAPI backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- FILE HANDLING --------------------
def ensure_data_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

#this function loads vectors from the data file and returns them as a list of dictionaries
def load_vectors() -> List[Dict[str, Any]]:
    ensure_data_file()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_vectors(data: List[Dict[str, Any]]):
    with _write_lock:
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, DATA_FILE)

# -------------------- TEXT EXTRACTION --------------------
def extract_text(upload: UploadFile) -> str:
    name = upload.filename.lower()
    raw = upload.file.read()
    upload.file.seek(0)

    if name.endswith(".txt"):
        return raw.decode("utf-8", errors="ignore")

    if name.endswith(".pdf"):
        return pdf_extract_text(BytesIO(raw))

    if name.endswith(".docx"):
        doc = docx.Document(BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs)

    raise HTTPException(status_code=400, detail="Unsupported file type")

# -------------------- CHUNKING --------------------
def chunk_text(text: str) -> List[str]:
    chunks = []
    start = 0
    text = text.strip()

    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end].strip())
        start = end - CHUNK_OVERLAP

    return [c for c in chunks if c]

# -------------------- EMBEDDINGS --------------------
#this function gets embeddings from openai for a list of texts and returns a list of embeddings
#for example if input is ["text1", "text2"], output will be [[emb1], [emb2]]
def get_embeddings(texts: List[str]) -> List[List[float]]:
    response = openai.Embedding.create(
        model=EMBEDDING_MODEL,
        input=texts
    )
    return [d["embedding"] for d in response["data"]] #return list of embeddings

# -------------------- SIMILARITY --------------------
#this function calculates cosine similarity between two vectors a and b
def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0

# -------------------- ANSWER GENERATION --------------------
def generate_answer(question: str, context_chunks: List[str]) -> str:
    context = "\n\n".join(context_chunks)

    prompt = f"""
You are a helpful assistant.
Answer the question ONLY using the context below.
If the answer is not present, say:
"I don't know based on the provided documents."

Context:
{context}

Question:
{question}

Answer:
"""

    response = openai.ChatCompletion.create(
        model=CHAT_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": "Answer like a knowledgeable human expert."},
            {"role": "user", "content": prompt}
        ]
    )

    return response["choices"][0]["message"]["content"].strip()

# -------------------- API ENDPOINTS --------------------
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"detail": str(exc)})

# ---------- ADMIN: UPLOAD ----------
@app.post("/api/admin/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    vectors = load_vectors()
    added = 0

    for file in files:
        try:
            text = extract_text(file)
            chunks = chunk_text(text)
            embeddings = get_embeddings(chunks)

            for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                vectors.append({
                    "id": str(uuid.uuid4()),
                    "filename": file.filename,
                    "chunk_index": idx,
                    "text": chunk,
                    "embedding": emb
                })
                added += 1

        except Exception as e:
            logger.error(f"Upload failed for {file.filename}: {e}")

    save_vectors(vectors)
    return {"status": "ok", "added_chunks": added}

# ---------- USER: QUERY ----------
@app.post("/api/user/query")
async def query(payload: Dict[str, Any]):
    # the payload is expected to be in the form:
    #{
        #"q": "How many sick leaves does SR Solutions have?"
    #}
    question = payload.get("q") # here q is question
    k = int(payload.get("k", TOP_K)) # number of top documents to consider

    if not question:#handle th e case when question is missing
        raise HTTPException(status_code=400, detail="Question missing")#raise an error if question is missing

    q_embedding = get_embeddings([question])[0]
    data = load_vectors() #load all vectors from the data file

    if not data:
        return {"answer": "No documents available.", "sources": []}

    scored = []
    for item in data:
        score = cosine_similarity(q_embedding, item["embedding"])
        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_items = scored[:k]

    context_chunks = [item["text"] for _, item in top_items]
    answer = generate_answer(question, context_chunks)

    sources = [
        {
            "filename": item["filename"],
            "chunk_index": item["chunk_index"],
            "score": round(score, 4)
        }
        for score, item in top_items
    ]

    return {
        "answer": answer,
    }
