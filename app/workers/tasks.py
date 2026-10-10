import logging
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

log = logging.getLogger("graphghost.jobs")

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
    log.info("Job %s queued: %s", job_id[:8], kind)
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
    urls = params["urls"] or [reel["url"] for reel in reel_store.list_reels(downloaded=False)]
    # The database decides what is already downloaded, not the files on disk;
    # force re-downloads (and overwrites) even those.
    skipped = []
    if not params["force"]:
        urls, skipped = reel_store.split_downloaded(urls)
    job["results"] = skipped
    # With nothing left to download the job still has work if downloaded Reels are
    # waiting for a transcript or analysis; only fail when there is nothing at all.
    nothing_for_ai = not (params["transcribe"] and reel_store.list_needing_ai())
    if not urls and not skipped and nothing_for_ai:
        raise ValueError(
            "Nothing to do: every collected Reel is already downloaded and processed."
        )
    log.info(
        "Download: %d to fetch, %d already downloaded (database)", len(urls), len(skipped)
    )

    def remember(result: dict, results: list[dict]) -> None:
        if result["ok"] and result["path"]:
            reel_store.save_download(result["url"], result["path"], result["details"])
        done = [{k: v for k, v in r.items() if k != "details"} for r in results]
        job.update(results=skipped + done)

    if urls:
        download_reels(urls, DOWNLOADS_DIR, headless=params["headless"], on_result=remember)

    # Only Reels that were never transcribed (or analysed) are picked up.
    if params["transcribe"] and reel_store.list_needing_ai():
        submit("transcribe", {})


def run_transcribe(job: dict) -> None:
    """Transcribe, then analyse, every downloaded Reel that has not been processed."""
    pending = reel_store.list_needing_ai()
    if not pending:
        raise ValueError("Nothing to transcribe: every downloaded Reel is already processed.")

    log.info("Transcribe: %d Reel(s) to process", len(pending))
    for number, reel in enumerate(pending, start=1):
        code = reel["code"]
        label = f"[{number}/{len(pending)}] {code}"
        result = {"code": code, "ok": False, "stage": "transcription", "message": ""}
        job["results"].append(result)
        try:
            transcript = reel["transcript"]
            if transcript is None:
                log.info("%s: transcribing %s", label, reel["video_path"])
                transcript = transcribe(Path(reel["video_path"]))
                reel_store.save_transcript(code, transcript)  # kept even if analysis fails
                log.info("%s: transcript saved (%d characters)", label, len(transcript))
            result["stage"] = "analysis"
            if transcript.strip():
                log.info("%s: analysing", label)
                analysis = analyze(transcript)
                reel_store.save_analysis(code, analysis)
                locations = len(analysis.get("addresses") or [])
                log.info("%s: analysis saved (%d location(s))", label, locations)
                result.update(ok=True, message="Transcribed and analysed.")
            else:
                log.info("%s: no speech found, analysis skipped", label)
                result.update(ok=True, message="No speech found; analysis skipped.")
        except Exception as error:
            result["message"] = str(error)
            log.error("%s: failed at %s: %s", label, result["stage"], error)


HANDLERS = {"collect": run_collect, "download": run_download, "transcribe": run_transcribe}


def worker_loop() -> None:
    while True:
        job = jobs[job_queue.get()]
        job["status"] = "running"
        name = f"{job['id'][:8]} ({job['kind']})"
        log.info("Job %s started", name)
        try:
            HANDLERS[job["kind"]](job)
            job["status"] = "done"
            # A job can finish with some items failed; say so rather than hide it.
            items = [r for r in job["results"] if isinstance(r, dict) and "ok" in r]
            failed = sum(1 for r in items if not r["ok"])
            if failed:
                log.warning("Job %s finished: %d ok, %d FAILED", name, len(items) - failed, failed)
            else:
                log.info("Job %s finished", name)
        except Exception as error:
            job.update(status="failed", error=str(error))
            log.error("Job %s failed: %s", name, error)
        finally:
            job_queue.task_done()


def start_worker() -> None:
    threading.Thread(target=worker_loop, name="job-worker", daemon=True).start()
