# RAG-QA — Local Retrieval-Augmented Generation System

A simple end-to-end RAG application built with:

- React (UI)
- FastAPI (Backend)
- OpenAI Embeddings
- Local JSON Vector Store (vectors.json)

Upload documents → extract text → chunk → embed → store → query using cosine similarity.

---

## Repository Structure

<img width="403" height="366" alt="image" src="https://github.com/user-attachments/assets/e9c24631-ccbd-4a6d-a1c0-7ff5ddc7765b" />


---

## Prerequisites

Backend:

pip install -r requirements.txt

create .env file and paste Open AI key
OPENAI_API_KEY="your key"

Frontend:

npm install

---

## Environment Variables

<img width="313" height="136" alt="image" src="https://github.com/user-attachments/assets/0f5f96ef-86af-42f4-a27f-07eb3c00e525" />

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
