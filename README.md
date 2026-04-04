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

  * `POST /media/upload-url` returns a local `PUT` URL.
  * Upload file bytes to that URL with `Authorization: Bearer <token>`.
  * Files are stored in `backend/uploads` and served from `/uploads/...`.
