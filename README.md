# mgdv-frame-extraction

Frame-extraction service for Marrying Ghana Dating member verification.
The dating site runs on Hostinger shared hosting with no FFmpeg and no
PHP shell execution, so the WordPress plugin cannot pull a frame out of a
member's intro video itself. This tiny service does that one job.

## What it does

`POST /extract` with header `X-Api-Key: <MGDV_API_KEY>` and a multipart
file field `video` (MP4 or WebM, max 20 MB) returns a single JPEG frame
taken ~0.5s into the video, scaled to 640px wide — the reference frame
Didit compares with the member's live selfie.

`GET /health` returns `{"ok": true}`.

## Privacy

- Every request's files live in a fresh temp directory that is deleted in
  a `finally` block, whether the request succeeds or fails.
- Nothing is stored, logged, or retained. No database, no disk writes
  outside the per-request temp dir, no analytics.
- Only the API key holder (the dating site's plugin) can call it.

## Deploy (Render, free tier, no card)

1. Push this folder to a GitHub repo.
2. In Render, create a Web Service from that repo (Docker environment,
   free plan). Set the `MGDV_API_KEY` env var to a long random secret and
   use the SAME secret in the WordPress plugin's Didit settings.
3. Note the service URL (https://mgdv-frame-extraction.onrender.com).

Free-tier note: Render's free service sleeps after 15 minutes without
traffic and takes ~1 minute to wake. The WordPress plugin must allow a
generous timeout (90s) on the call. If verification volume grows, move
to a paid Render plan (~$7/mo) so the service stays awake.

## Local test

```sh
pip install -r requirements.txt
MGDV_API_KEY=test-secret uvicorn app:app --port 8000
curl -X POST http://localhost:8000/extract \
  -H "X-Api-Key: test-secret" \
  -F "video=@sample.mp4" --output frame.jpg
```
