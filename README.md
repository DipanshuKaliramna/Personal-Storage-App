# StorageApp (UI Like Instagram)

Private photo/video storage with per-user quotas, sharing links, and albums.

## Stack
- Backend: FastAPI + Postgres + S3 (AWS)
- Frontend: React (Vite)

## Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## Notes
- Default quota: 15 GB free, 25 GB premium.
- Upload flow: request presigned URL, upload to S3, then list in feed.
- Local mode (no AWS): set `STORAGE_BACKEND=local` in `backend/.env`.
  - `POST /media/upload-url` returns a local `PUT` URL.
  - Upload file bytes to that URL with `Authorization: Bearer <token>`.
  - Files are stored in `backend/uploads` and served from `/uploads/...`.
