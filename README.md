# Sententia.ai

AI-powered cross-border fund structuring MVP. Proposes investment structures and validates compliance for multi-jurisdiction FDI scenarios.

**Stack:** Next.js (Cloudflare Pages) · FastAPI (Hugging Face Spaces) · Supabase · Qdrant · OPA

---

## Quick Start

### Prerequisites
- Node.js 18+
- Python 3.11+
- Git

---

## 1. Clone & configure environment

```bash
git clone <your-repo-url>
cd MNLU_sententia_AI

# Copy env templates
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
```

Fill in your API keys in each `.env` file. See sign-up links inside `.env.example`.

---

## 2. Set up Supabase (free, ~5 min)

1. Go to [https://supabase.com/](https://supabase.com/) → **Start your project** → sign in with GitHub
2. Click **New project** → choose a name (e.g. `sententia`) → set a strong DB password → pick a region → **Create new project** (takes ~2 min)
3. Once ready, go to **Settings → API** → copy:
   - `Project URL` → paste as `SUPABASE_URL` in your `.env`
   - `anon public` key → paste as `SUPABASE_ANON_KEY`
   - `service_role` key → paste as `SUPABASE_SERVICE_ROLE_KEY`
4. Go to **SQL Editor** → click **New query** → paste the contents of `supabase/migrations/0001_initial_schema.sql` → click **Run**
5. Go to **Table Editor** — you should see 6 tables: `users`, `firm_workspaces`, `scenarios`, `structures`, `review_queue`, `audit_log`

---

## 3. Set up Qdrant (free, ~5 min)

1. Go to [https://cloud.qdrant.io/](https://cloud.qdrant.io/) → sign up → **Create cluster**
2. Choose **Free tier** → name it `sententia` → pick a cloud region → **Create**
3. Once ready, go to **Access** → **Create API key** → copy it
4. Copy the **Cluster URL** (format: `https://xxxx.region.gcp.cloud.qdrant.io`)
5. Paste both into your `.env` as `QDRANT_URL` and `QDRANT_API_KEY`
6. Run the setup script to create the collection:

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python scripts/setup_qdrant.py
```

You should see: `✅ Collection 'sententia_legal_corpus' created successfully.`

---

## 4. Run the backend

```bash
cd backend
# (activate venv if not already)
uvicorn app.main:app --reload --port 8000
```

Test: open [http://localhost:8000/health](http://localhost:8000/health) — should return JSON with `status: "ok"`.

---

## 5. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) — you'll see the Sententia.ai landing page with a live health status from the backend.

---

## 6. Deploy

### Frontend → Cloudflare Pages
1. Push this repo to GitHub
2. Go to [Cloudflare Pages](https://pages.cloudflare.com/) → **Create a project** → connect your GitHub repo
3. Set **Build command:** `npm run build` · **Build output directory:** `out` · **Root directory:** `frontend`
4. Add env var: `NEXT_PUBLIC_API_URL` = your HF Spaces backend URL

### Backend → Hugging Face Spaces
1. Go to [https://huggingface.co/spaces](https://huggingface.co/spaces) → **Create new Space**
2. Choose **Docker** SDK → name it `sententia-backend`
3. Push the `backend/` folder contents to the Space repo (or use the HF CLI)
4. Add all env vars in **Settings → Variables and secrets**
5. The Space will build and expose port `7860` automatically

---

## Project Structure

```
├── .env.example              ← env template (safe to commit)
├── .gitignore
├── README.md
├── frontend/                 ← Next.js 14, App Router
│   └── src/app/
├── backend/                  ← FastAPI, Python 3.11
│   ├── app/
│   ├── scripts/
│   └── Dockerfile
└── supabase/
    └── migrations/
        └── 0001_initial_schema.sql
```
