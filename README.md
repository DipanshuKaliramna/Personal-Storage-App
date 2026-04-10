# StorageApp (UI Like Instagram)

Private file storage with per-user quotas, sharing links, and albums.

## Motivation

While using Google Drive for storing personal files, I often found the interface cluttered and difficult to navigate when trying to quickly find specific media. Over time, as more files accumulated, managing them became increasingly complex.

To solve this problem, I decided to build my own personal storage platform that focuses on a **clean, simple, and media-centric experience**, similar to an Instagram-style feed where photos, videos, PDFs, and other files are easier to browse and organize.

This project is my attempt to create a **personal storage space** that is easier to use, visually organized, and gives the user more control over their stored media.

## Stack

* Backend: FastAPI + Postgres + S3 (AWS)
* Frontend: React (Vite)

## Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## Notes

* Default quota: 15 GB free, 25 GB premium.
* Upload flow: request presigned URL, upload to S3, then list in feed.
* Local mode (no AWS): set `STORAGE_BACKEND=local` in `backend/.env`.
* For deployment, set `PUBLIC_BASE_URL` to your backend's public HTTPS URL and `CORS_ALLOWED_ORIGINS` to the frontend origin(s), comma-separated.
* Frontend deployments should set `VITE_API_BASE_URL` to the public backend URL.
* Backend health checks can target `GET /healthz`.
* The backend no longer creates or patches tables on startup. Run Alembic migrations explicitly before starting the app.

  * `POST /media/upload-url` returns a local `PUT` URL.
  * Upload file bytes to that URL with `Authorization: Bearer <token>`.
  * Files are stored in `backend/uploads`.

## Deploy Checklist

```bash
# backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

If your database already existed before Alembic was added and already has the app tables, run this once instead of `alembic upgrade head`:

```bash
alembic stamp head
```

After that, future schema changes should use normal Alembic upgrades.

Set these backend env vars before deploying:

* `ENV=prod`
* `DEBUG=false`
* `DATABASE_URL=...`
* `JWT_SECRET=...`
* `PUBLIC_BASE_URL=https://your-api-domain`
* `CORS_ALLOWED_ORIGINS=https://your-frontend-domain`
* `STORAGE_BACKEND=local` or `STORAGE_BACKEND=s3`
* `S3_BUCKET`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` when using S3

If you deploy with Docker, [backend/Dockerfile](/home/dipanshu/Desktop/Projects/Storageapp(UILikeInsta)/backend/Dockerfile) runs migrations before starting Uvicorn.
