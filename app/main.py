import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.models import reels as reel_store
from app.models.migrate import apply_migrations
from app.workers import tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    apply_migrations()  # fail fast if the database is unreachable
    tasks.start_worker()
    yield


app = FastAPI(title="GraphGhost", lifespan=lifespan)


class CollectRequest(BaseModel):
    group: str = Field(min_length=1, description="Exact group name as shown in Messages")
    max_scrolls: int = Field(default=200, ge=1)
    headless: bool = False
    download: bool = Field(
        default=True, description="Queue a download of the new Reels when collection finishes"
    )
    transcribe: bool = Field(
        default=True, description="Transcribe and analyse downloaded Reels afterwards"
    )


class DownloadRequest(BaseModel):
    urls: list[str] = Field(
        default_factory=list,
        description="Reel URLs to download; empty means every collected Reel not downloaded yet",
    )
    headless: bool = True
    transcribe: bool = Field(
        default=True, description="Transcribe and analyse downloaded Reels afterwards"
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/collect", status_code=202)
def start_collection(request: CollectRequest) -> dict:
    """Queue a job that collects Reel URLs from a group."""
    return {"job_id": tasks.submit("collect", request.model_dump())}


@app.post("/download", status_code=202)
def start_download(request: DownloadRequest) -> dict:
    """Queue a job that downloads Reels (saved URLs unless urls are given)."""
    return {"job_id": tasks.submit("download", request.model_dump())}


@app.post("/transcribe", status_code=202)
def start_transcription() -> dict:
    """Queue transcription and analysis of downloaded Reels that have none yet."""
    return {"job_id": tasks.submit("transcribe", {})}


@app.get("/jobs")
def list_jobs() -> list[dict]:
    return list(tasks.jobs.values())


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    if job_id not in tasks.jobs:
        raise HTTPException(404, "Unknown job id.")
    return tasks.jobs[job_id]


def with_video_url(reel: dict) -> dict:
    """Add the API link for the video next to its stored relative video_path."""
    reel["video_url"] = f"/downloads/{reel['code']}" if reel["video_path"] else None
    return reel


@app.get("/reels")
def list_reels(downloaded: bool | None = None) -> dict:
    """All collected Reels with their details; filter with ?downloaded=true|false."""
    return {"reels": [with_video_url(reel) for reel in reel_store.list_reels(downloaded)]}


@app.get("/reels/{code}")
def get_reel(code: str) -> dict:
    reel = reel_store.get_reel(code)
    if reel is None:
        raise HTTPException(404, "Unknown Reel code.")
    return with_video_url(reel)


@app.get("/downloads")
def list_downloads() -> dict:
    if not tasks.DOWNLOADS_DIR.exists():
        return {"files": []}
    return {"files": sorted(path.name for path in tasks.DOWNLOADS_DIR.glob("*.mp4"))}


@app.get("/downloads/{code}")
def get_download(code: str) -> FileResponse:
    """Return a downloaded video by Reel code (with or without .mp4), using the stored path."""
    code = code.removesuffix(".mp4")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", code):  # also blocks path traversal
        raise HTTPException(400, "Invalid Reel code.")

    reel = reel_store.get_reel(code)
    stored = reel["video_path"] if reel else None
    path = Path(stored) if stored else tasks.DOWNLOADS_DIR / f"{code}.mp4"
    # video_path is relative to the project root; never serve outside it.
    if not path.resolve().is_relative_to(Path.cwd().resolve()) or not path.is_file():
        raise HTTPException(404, "Not downloaded yet.")
    return FileResponse(path, media_type="video/mp4")
