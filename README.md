# RAG-QA — Local Retrieval-Augmented Generation System

A simple end-to-end RAG application built with:

- React (UI)
- FastAPI (Backend)
- OpenAI Embeddings
- Local JSON Vector Store (vectors.json)

Upload documents → extract text → chunk → embed → store → query using cosine similarity.

---

## Repository Structure

RAG-QA/
├─ backend/
│  ├─ app.py
│  ├─ data/
│  │  └─ vectors.json
│  ├─ error.log
│  └─ .env
└─ web/
   ├─ src/
   │  ├─ pages/
   │  │  ├─ AdminPage.tsx
   │  │  └─ UserChat.tsx
   └─ package.json

---

## Prerequisites

Backend:

pip install fastapi uvicorn python-dotenv openai python-multipart pdfminer.six python-docx

Frontend:

npm install

---

## Environment Variables

Backend .env:

OPENAI_API_KEY=your-key
CHUNK_SIZE=800
CHUNK_OVERLAP=150
EMBEDDING_MODEL=text-embedding-3-small
TOP_K=3

Frontend .env:

REACT_APP_API_BASE=http://localhost:8000

---

## Run

Start backend:

cd backend
uvicorn app:app --reload --port 8000

Start frontend:

cd web
npm start

---

## API

POST /api/admin/upload  
POST /api/admin/clear  
POST /api/user/query

---

## Reset Vectors

Replace vectors.json content with:

[]

---

## Testing

Ask questions such as:

- What services does SR Solutions provide?
- What are the HR policies?
- How many annual paid leave days are allowed?

---

## Notes

- Works with txt/pdf/docx  
- Stores vectors locally  
- Simple and extensible RAG pipeline  
