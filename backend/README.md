# Backend Deployment

This backend is set up to deploy with Alembic-managed schema migrations.

## Local run

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in the real values.

3. Apply migrations:

```bash
alembic upgrade head
```

4. Start the API:

```bash
uvicorn app.main:app --reload
```

## Production deploy

Set these environment variables on your host:

- `DATABASE_URL`
- `SECRET_KEY`
- `APP_ENV=production`
- `ALLOWED_ORIGINS`
- `COOKIE_SECURE=true`

If your platform supports Docker, deploy from this folder with the included `Dockerfile`.
The container start command automatically runs `alembic upgrade head` before starting Uvicorn.

## Future schema changes

Create a migration after model changes:

```bash
alembic revision --autogenerate -m "describe change"
```

Apply it:

```bash
alembic upgrade head
```