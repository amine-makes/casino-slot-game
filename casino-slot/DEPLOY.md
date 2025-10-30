# Casino Slot – Deployment Cheatsheet

This repository is preconfigured for a quick, reliable deploy:

- Frontend: Netlify (static hosting + Edge Function to proxy `/api/*`)
- Backend: Render (Python, Gunicorn), or your own server

## 1) Push this repo to GitHub

```bash
cd /home/amine/PythonProjects/casino-slot
git init
git add .
git commit -m "Initial commit: casino slot + netlify edge + render"
# Create a new GitHub repo (in the UI) and copy its remote URL, then:
git remote add origin https://github.com/<your-user>/<your-repo>.git
git branch -M main
git push -u origin main
```

## 2) Backend on Render (2 minutes)

- In Render: New → Blueprint → choose this repo
- Confirm `render.yaml` and click Deploy
- After it’s live, copy the Render URL (e.g., `https://casino-slot-backend.onrender.com`)
- Set environment variables in the Render service:
  - `ADMIN_TOKEN` = a strong secret
  - Optional: `SIGNING_REQUIRED_ADMIN`, `SIGNING_SECRET`, `ALLOWED_ADMIN_IPS`, `ALLOWED_ORIGINS`

## 3) Frontend on Netlify (1–2 minutes)

- In Netlify: Add new site → Import from Git → select this repo
- No build command; Publish directory = `frontend`
- Site settings → Environment variables:
  - `BACKEND_ORIGIN` = the Render URL from step 2
- Deploy site

The Edge Function at `netlify/edge-functions/proxy.js` forwards `/api/*` to `BACKEND_ORIGIN`, so the frontend can call `/api` same-origin.

## 4) Quick validation

- Visit your Netlify URL → loads `index_professional.html`
- Open devtools Network tab
  - `/api/health` should return `{ status: "ok" }`
  - Create a session and spin; Wallet and Transactions update
- Admin dashboard `/admin.html`:
  - Set API Base to `/api` and paste your `ADMIN_TOKEN`
  - Load Summary/Events; inspect Support Threads & Messages

## Optional local demo backend

If you want to demo quickly without Render:

- Start backend locally (port 5000) and expose it with `ngrok http 5000`
- Set Netlify `BACKEND_ORIGIN` to the `https://` ngrok URL

## Notes

- Strict CSP is enforced on the professional page; no inline JS/CSS
- Support chat AI is optional (DeepSeek/OpenAI-compatible): set `AI_API_BASE`, `AI_API_KEY`, `AI_MODEL` on the backend to enable
- SQLite DB persists on the backend host; for Docker use a volume; for Render it’s ephemeral—use an external DB if needed for production
