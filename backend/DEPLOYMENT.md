# Deploying the Backend to Render

This document describes the minimal steps and environment variables needed to deploy the FastAPI backend on Render (or similar PaaS) and how to connect it to the Vercel frontend.

1) Required environment variables
- `DATABASE_URL` — full Postgres connection string (Supabase). Example: `postgresql://user:pass@host:5432/dbname`
- `SECRET_KEY` — application secret used for JWTs/cookies
- `FRONTEND_URL` — public URL of the frontend (used to build invite links)
- `ALLOWED_ORIGINS` — comma-separated list of allowed CORS origins (e.g. `https://yourfrontend.com`)
- `COOKIE_DOMAIN` — domain to set for cookies (optional)
- `COOKIE_SECURE` — `true` or `false` (set `true` in production with HTTPS)
- Mail (optional): `MAIL_HOST`, `MAIL_PORT`, `MAIL_USER`, `MAIL_PASSWORD`, `MAIL_FROM`

2) One-time setup steps
- Create a Render Web Service (Python) and add the environment variables above in the Render dashboard.
- Add the `DATABASE_URL` from Supabase to Render's env.
- (Optional) Run migrations once from the Render shell or locally:

```bash
# Activate your Python env, then from backend/ directory:
pip install -r requirements.txt
alembic upgrade head
```

3) Start command
- Use a production ASGI server. Example start command (Render `Start Command`):

```bash
gunicorn -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:$PORT --workers 3
```

Alternatively, make the repository include `start-prod.sh` and point Render to run `bash start-prod.sh`.

4) Notes & checklist
- Ensure `FRONTEND_URL` matches the Vercel deployment URL so invite links point to the right site.
- If mail credentials are not supplied, the backend's mailer is a safe no-op and will log that it skipped sends. You can add an HTTP mail provider later (SendGrid/Mailgun) — the codebase can be extended to support it.
- Set `ALLOWED_ORIGINS` so the backend CORS allows the frontend domain.
- Configure cookie settings: set `COOKIE_DOMAIN`, `COOKIE_SECURE=true`, and ensure your frontend uses the backend domain for requests when storing httponly cookies.

5) Debugging tips
- If you see DNS resolution errors for the `DATABASE_URL` host, verify network/DNS (possible IPv6 issues). Try forcing IPv4 or confirm the host is resolvable from Render's region.
- Use Render's shell to run `python -c "from app.database import engine; print('OK', engine)"` to confirm DB connectivity.

If you'd like, I can also add a `render.yaml` example or add deploy-time scripts for running Alembic migrations automatically.
