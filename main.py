from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time, threading, uuid, os, hmac, hashlib, json, requests

# ---------------- App & CORS ----------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # For testing. Later: restrict to your Base44 app domain.
    allow_credentials=True,
    allow_methods=["*"],          # Enables POST, GET, OPTIONS, etc.
    allow_headers=["*"],
)

# ---------------- In-memory job store (demo) ----------------
JOBS = {}

# ---------------- Models ----------------
class Clip(BaseModel):
    url: str

class Music(BaseModel):
    url: str | None = None

class Params(BaseModel):
    aspect_ratio: str = "9:16"
    target_duration_sec: int = 60
    mood: str = "Luxury"

class CreateJob(BaseModel):
    clips: list[Clip]
    music: Music | None = None
    params: Params
    webhook_url: str | None = None   # Base44 can send this

# ---------------- Health ----------------
@app.get("/health")
def health():
    return {"ok": True}

# ---------------- Webhook helper ----------------
def send_webhook(webhook_url: str, payload: dict):
    """
    Sends a signed webhook to Base44 with X-ReelForge-Signature header.
    Secret must match what's set in Base44 Settings (Webhook Secret).
    """
    secret = os.getenv("WEBHOOK_SECRET", "")
    body = json.dumps(payload)
    signature = hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-ReelForge-Signature": signature
    }
    try:
        requests.post(webhook_url, data=body, headers=headers, timeout=15)
    except Exception as e:
        # For demo: just print. In prod, log to your logger.
        print(f"[webhook] failed: {e}")

# ---------------- Fake worker (demo processing) ----------------
def fake_worker(job_id: str, webhook_url: str | None):
    JOBS[job_id]["status"] = "processing"
    for p in range(1, 6):
        time.sleep(2)  # pretend we're processing
        JOBS[job_id]["progress"] = p * 20

    # Pretend finished video URL (replace with your S3 URL later)
    download_url = "https://sample-videos.com/video321/mp4/360/big_buck_bunny_360p_1mb.mp4"
    JOBS[job_id]["status"] = "ready"
    JOBS[job_id]["download_url"] = download_url

    # If Base44 provided a webhook URL, notify them that the job is ready.
    if webhook_url:
        payload = {
            "job_id": job_id,
            "status": "ready",
            "download_url": download_url
        }
        send_webhook(webhook_url, payload)

# ---------------- API: create job ----------------
@app.post("/jobs")
def create_job(body: CreateJob):
    job_id = "J_" + uuid.uuid4().hex[:8]
    JOBS[job_id] = {
        "status": "queued",
        "progress": 0,
        "download_url": None,
        "error": None
    }
    threading.Thread(
        target=fake_worker,
        args=(job_id, body.webhook_url),
        daemon=True
    ).start()
    return {"job_id": job_id, "status": JOBS[job_id]["status"]}

# ---------------- API: get job status ----------------
@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    return JOBS.get(job_id, {"error": "not_found"})
