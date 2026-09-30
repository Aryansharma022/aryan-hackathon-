# Adaptive Assessment Engine

Standalone assessment module with a React/Vite client and FastAPI service.

## Run locally

1. Backend: `cd backend`, create a virtual environment, install `pip install -r requirements.txt`, then run `uvicorn app.main:app --reload`.
2. Copy `backend/.env.example` to `backend/.env`. Set `OPENAI_API_KEY` and optionally `MONGODB_URL`. Without an OpenAI key the service uses its clearly identified demo question bank.
3. Frontend: `cd frontend`, run `npm install` and `npm run dev`. Set `VITE_API_URL` only if the API runs somewhere other than `http://localhost:8000`.

## Deploy

- GitHub Pages builds the frontend from `frontend/` using `.github/workflows/deploy-pages.yml`.
- Deploy the backend by creating a Render Blueprint from this repository; `render.yaml` defines the FastAPI service.
- The Pages build uses `https://aryan-hackathon-assessment-api.onrender.com` by default. If Render assigns a different URL, add a GitHub Actions repository variable named `VITE_API_URL` with the actual service URL, then rerun the Pages workflow.
- `FRONTEND_ORIGINS` configures the backend CORS allowlist. Keep the GitHub Pages origin in that list.

Question answers are held server-side and never included in active question responses. MongoDB is optional for local demo mode; in-memory storage is used when it is not configured.
