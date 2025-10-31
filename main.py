from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time, threading, uuid

# Initialize app
app = FastAPI()

# ---- CORS FIX ----
# This allows your Base44 web app to send requests to your backend
# (especially the OPTIONS request that was failing earlier)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # For testing; later restrict to your Base44 app domain
    allow_credentials=True,
    allow_methods=["*"],          # Enables POST, GET, OPTIONS, etc.
    allow_headers=["*"],
)
# -------------------

JOBS = {}

# --- Models ---
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
    webhook_url: str | None = None


@app.get("/health")
def health():
    return {"ok": True}


def fake_worker(job_id: str):
    """Simulates video processing for demo purposes."""
    JOBS[job_id]["status"] = "processing"
    for p in range(1, 6):
        time.sleep(2)
        JOBS[job_id]["progress"] = p * 20
    JOBS[job_id]["status"] = "ready"
    JOBS[job_id]["download_url"] = (
        "https://sample-videos.com/video321/mp4/360/big_buck_bunny_360p_1mb.mp4"
    )


@app.post("/jobs")
def create_job(body: CreateJob):
    job_id = "J_" + uuid.uuid4().hex[:8]
    JOBS[job_id] = {"status": "queued", "progress": 0, "download_url": None, "error": None}
    threading.Thread(target=fake_worker, args=(job_id,), daemon=True).start()
    return {"job_id": job_id, "status": JOBS[job_id]["status"]}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    return JOBS.get(job_id, {"error": "not_found"})
