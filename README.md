# Adaptive Assessment Engine

Standalone assessment module with a React/Vite client and FastAPI service.

## Run locally

1. Backend: `cd backend`, create a virtual environment, install `pip install -r requirements.txt`, then run `uvicorn app.main:app --reload`.
2. Copy `backend/.env.example` to `backend/.env`. Set `OPENAI_API_KEY` and optionally `MONGODB_URL`. Without an OpenAI key the service uses its clearly identified demo question bank.
3. Frontend: `cd frontend`, run `npm install` and `npm run dev`. Set `VITE_API_URL` only if the API runs somewhere other than `http://localhost:8000`.

Question answers are held server-side and never included in active question responses. MongoDB is optional for local demo mode; in-memory storage is used when it is not configured.
