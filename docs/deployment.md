# Deploying DocuMind

Two pieces, two hosts:
- **Backend** (FastAPI + ChromaDB) → **Render** (Docker web service). Needs a real
  container with disk; can't be serverless because it loads an embedding model and a
  vector index.
- **Frontend** (Next.js) → **Vercel** (built for Next.js).

There's a small chicken-and-egg with CORS: the backend must allow the frontend's URL,
and the frontend must know the backend's URL. We solve it by deploying the backend
first, then the frontend, then setting one env var on each. Follow the order below.

Prerequisites: the repo is pushed to GitHub (done), and you have a Render account and a
Vercel account (both free, sign in with GitHub).

---

## Step 1 — Deploy the backend to Render

The repo already contains `Dockerfile` and `render.yaml`. The image ingests the sample
handbook at build time, so the demo works immediately.

1. Go to **dashboard.render.com → New → Blueprint**.
2. Connect the GitHub repo `ankitsingh711/GenAI-RAG`. Render detects `render.yaml`.
3. It will create a service named **documind-api**. Before the first deploy, set the
   secret env var when prompted (or under the service's **Environment** tab):
   - `ANTHROPIC_API_KEY` = your real key (`sk-ant-...`).
   - Leave `FRONTEND_ORIGIN` blank for now — you'll fill it in Step 3.
4. Click **Apply / Create**. First build takes a few minutes (it downloads the base
   image, installs deps, downloads the embedding model, and ingests).
5. When it's live, note the URL, e.g. `https://documind-api.onrender.com`. Test it:
   ```bash
   curl https://documind-api.onrender.com/health         # {"status":"ok"}
   curl https://documind-api.onrender.com/sources        # the sample handbook
   ```

> **Free tier note:** the service sleeps after ~15 min idle; the next request wakes it
> (a few seconds). 512 MB RAM is usually enough; if a cold start OOMs, bump the plan to
> "starter" in `render.yaml` (`plan: starter`) or the dashboard.

---

## Step 2 — Deploy the frontend to Vercel

1. Go to **vercel.com → Add New → Project** and import the same GitHub repo.
2. **Important:** set **Root Directory** to `web` (the repo root is the Python project;
   the Next.js app lives in `web/`). Vercel then auto-detects Next.js.
3. Add an environment variable:
   - `NEXT_PUBLIC_API_URL` = your Render backend URL from Step 1
     (e.g. `https://documind-api.onrender.com`, no trailing slash).
   - This is read at build time by `web/lib/api.ts`.
4. Click **Deploy**. Note the resulting URL, e.g. `https://genai-rag.vercel.app`.

---

## Step 3 — Connect them (CORS)

The browser will block the frontend from calling the backend until the backend says the
frontend's origin is allowed.

1. Back in Render → documind-api → **Environment**:
   - Set `FRONTEND_ORIGIN` = your Vercel URL (e.g. `https://genai-rag.vercel.app`).
   - Save → Render redeploys automatically.
2. Open your Vercel URL. Ask a question — you should see the answer stream in, and the
   sidebar list the sample handbook.

That's it — DocuMind is live.

---

## Updating after changes

Both hosts auto-deploy on push to `main`:
- Push backend changes → Render rebuilds the image (re-ingests the sample doc).
- Push frontend changes → Vercel rebuilds.

To change which documents are indexed in production, add files under `data/` and push —
they're baked into the image at build time. (A nicer long-term design is an upload
endpoint writing to a persistent disk or object storage; see `docs/production.md`.)

## Run it locally (unchanged)

```bash
# from genai-rag/
uv run uvicorn documind.api.app:app --reload --port 8000   # terminal 1
cd web && pnpm dev                                          # terminal 2
```
`FRONTEND_ORIGIN` is unset locally, so CORS defaults to allowing `http://localhost:3000`.
