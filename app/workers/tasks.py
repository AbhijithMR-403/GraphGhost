import queue
import threading
import uuid
from pathlib import Path

from app.models import reels as reel_store
from app.scraper.collector import collect_group_reels, write_urls
from app.scraper.downloader import download_reels
from app.services.reel_analysis import analyze
from app.services.transcription import transcribe

OUTPUT_PATH = Path("reel_urls.txt")
DOWNLOADS_DIR = Path("downloads")

# A simple in-process message queue. Collecting and downloading share one
# logged-in browser profile, so a single worker thread runs one job at a time
# and later jobs wait in the queue. Jobs are kept in memory and are lost on
# restart; results are on disk (OUTPUT_PATH, DOWNLOADS_DIR).
jobs: dict[str, dict] = {}
job_queue: queue.Queue = queue.Queue()


def submit(kind: str, params: dict) -> str:
    """Put a job on the queue and return its id."""
    job_id = uuid.uuid4().hex
    jobs[job_id] = {
        "id": job_id,
        "kind": kind,
        "status": "queued",
        "params": params,
        "results": [],
        "error": None,
    }
    job_queue.put(job_id)
    return job_id


def run_collect(job: dict) -> None:
    params = job["params"]

    def remember(url: str, urls: list[str]) -> None:
        reel_store.add_reel(url, params["group"])
        job.update(results=list(urls))

    collect_group_reels(
        params["group"],
        OUTPUT_PATH,
        params["max_scrolls"],
        params["headless"],
        on_url=remember,
    )
    # reel_urls.txt holds every Reel ever collected, not just this run.
    write_urls(OUTPUT_PATH, [reel["url"] for reel in reel_store.list_reels()])

    if params["download"] and reel_store.list_reels(downloaded=False):
        submit(
            "download",
            {"urls": [], "headless": True, "transcribe": params["transcribe"]},
        )


def run_download(job: dict) -> None:
    params = job["params"]
    urls = params["urls"] or [
        reel["url"] for reel in reel_store.list_reels(downloaded=False)
    ]
    if not urls:
        raise ValueError("Nothing to download: every collected Reel is already downloaded.")

    def remember(result: dict, results: list[dict]) -> None:
        if result["ok"] and result["path"]:
            reel_store.save_download(result["url"], result["path"], result["details"])
        job.update(results=[{k: v for k, v in r.items() if k != "details"} for r in results])

    download_reels(urls, DOWNLOADS_DIR, headless=params["headless"], on_result=remember)

    # Only Reels that were never transcribed (or analysed) are picked up.
    if params["transcribe"] and reel_store.list_needing_ai():
        submit("transcribe", {})


def run_transcribe(job: dict) -> None:
    """Transcribe, then analyse, every downloaded Reel that has not been processed."""
    pending = reel_store.list_needing_ai()
    if not pending:
        raise ValueError("Nothing to transcribe: every downloaded Reel is already processed.")

    for reel in pending:
        code = reel["code"]
        result = {"code": code, "ok": False, "stage": "transcription", "message": ""}
        job["results"].append(result)
        try:
            transcript = reel["transcript"]
            if transcript is None:
                transcript = transcribe(Path(reel["video_path"]))
                reel_store.save_transcript(code, transcript)  # kept even if analysis fails
            result["stage"] = "analysis"
            if transcript.strip():
                reel_store.save_analysis(code, analyze(transcript))
                result.update(ok=True, message="Transcribed and analysed.")
            else:
                result.update(ok=True, message="No speech found; analysis skipped.")
        except Exception as error:
            result["message"] = str(error)


HANDLERS = {"collect": run_collect, "download": run_download, "transcribe": run_transcribe}


def worker_loop() -> None:
    while True:
        job = jobs[job_queue.get()]
        job["status"] = "running"
        try:
            HANDLERS[job["kind"]](job)
            job["status"] = "done"
        except Exception as error:
            job.update(status="failed", error=str(error))
        finally:
            job_queue.task_done()


def start_worker() -> None:
    threading.Thread(target=worker_loop, name="job-worker", daemon=True).start()
