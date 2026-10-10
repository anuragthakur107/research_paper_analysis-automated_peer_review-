
import os
import uuid
import shutil
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Any

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

from graph import run_pipeline

app = FastAPI(
    title="Automated Peer Review API",
    description="AI-powered IEEE paper reviewer using LangGraph + Groq",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Storage ───────────────────────────────────────────────────────────────────
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

jobs: dict[str, dict[str, Any]] = {}

def _run_review_job(job_id: str, pdf_path: str):
    """Blocking pipeline call — runs in a thread via BackgroundTasks."""
    try:
        jobs[job_id]["status"] = "processing"
        report = run_pipeline(pdf_path)
        jobs[job_id]["status"] = "done"
        jobs[job_id]["report"] = report
        jobs[job_id]["completed_at"] = datetime.now().isoformat()
    except Exception as exc:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(exc)
    finally:
        # Clean up uploaded file
        try:
            os.remove(pdf_path)
        except OSError:
            pass


def _validate_pdf(file: UploadFile) -> None:
    """Raise 400 if the upload is not a PDF (checks filename + content-type)."""
    name_ok = file.filename.lower().endswith(".pdf")
    mime_ok = file.content_type in ("application/pdf", "application/octet-stream", None)
    if not name_ok:
        raise HTTPException(status_code=400, detail="Only PDF files are accepted (.pdf extension required).")
    if not mime_ok:
        raise HTTPException(status_code=400, detail=f"Invalid content-type '{file.content_type}'. Expected application/pdf.")



@app.get("/health")
def health():
    """Quick health check."""
    return {
        "status": "ok",
        "groq_key_set":   bool(os.getenv("GROQ_API_KEY")),
        "serpapi_key_set": bool(os.getenv("SERPAPI_KEY")),
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/review")
async def submit_review(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """
    Upload a PDF and start the peer-review pipeline.
    Returns a job_id immediately. Poll /report/{job_id} for results.
    """
    _validate_pdf(file)

    # Save uploaded PDF
    job_id = str(uuid.uuid4())
    pdf_path = UPLOAD_DIR / f"{job_id}.pdf"

    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Register job
    jobs[job_id] = {
        "job_id":      job_id,
        "filename":    file.filename,
        "status":      "queued",
        "report":      None,
        "error":       None,
        "submitted_at": datetime.now().isoformat(),
        "completed_at": None,
    }

    # Run pipeline in background thread (non-blocking)
    background_tasks.add_task(_run_review_job, job_id, str(pdf_path))

    return JSONResponse(
        status_code=202,
        content={
            "job_id":  job_id,
            "status":  "queued",
            "message": "Review started. Poll /report/{job_id} for results.",
        },
    )


@app.post("/review/sync")
async def submit_review_sync(file: UploadFile = File(...)):
    """
    Synchronous version — waits for the full pipeline and returns the report.
    Use for testing / small papers. May time out on slow connections.
    """
    _validate_pdf(file)

    job_id = str(uuid.uuid4())
    pdf_path = UPLOAD_DIR / f"{job_id}.pdf"

    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        report = await asyncio.get_running_loop().run_in_executor(None, run_pipeline, str(pdf_path))
        return JSONResponse(status_code=200, content={"status": "done", "report": report})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(exc)}")
    finally:
        try:
            os.remove(pdf_path)
        except OSError:
            pass


@app.get("/report/{job_id}")
def get_report(job_id: str):
    """
    Poll for job status and results.
    Status values: queued | processing | done | error
    """
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    if job["status"] == "done":
        return JSONResponse(status_code=200, content={
            "job_id":       job_id,
            "status":       "done",
            "filename":     job["filename"],
            "submitted_at": job["submitted_at"],
            "completed_at": job["completed_at"],
            "report":       job["report"],
        })

    if job["status"] == "error":
        return JSONResponse(status_code=500, content={
            "job_id":  job_id,
            "status":  "error",
            "error":   job["error"],
        })

    # still queued or processing
    return JSONResponse(status_code=202, content={
        "job_id":       job_id,
        "status":       job["status"],
        "filename":     job["filename"],
        "submitted_at": job["submitted_at"],
        "message":      "Still processing. Try again in a few seconds.",
    })


@app.get("/jobs")
def list_jobs():
    """List all jobs with their statuses (dev/debug endpoint)."""
    return [
        {
            "job_id":       jid,
            "filename":     j["filename"],
            "status":       j["status"],
            "submitted_at": j["submitted_at"],
            "completed_at": j.get("completed_at"),
        }
        for jid, j in jobs.items()
    ]


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)