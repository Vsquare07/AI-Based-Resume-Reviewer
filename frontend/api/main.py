import asyncio
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

# Add repository root to Python path so we can import the pipeline modules
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Load pipeline entrypoint explicitly from repo root main.py using importlib
# to avoid naming collision with this file (frontend/api/main.py)
import importlib.util

root_main_path = REPO_ROOT / "main.py"
spec = importlib.util.spec_from_file_location("root_pipeline_main", str(root_main_path))
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load module spec from {root_main_path}")
root_main_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(root_main_module)
run_pipeline = getattr(root_main_module, "run_pipeline")

from database import Base, engine, get_db
from models import Review

# Initialize SQLite tables
Base.metadata.create_all(bind=engine)

# Ensure candidate_name column exists for backwards-compatibility
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE reviews ADD COLUMN candidate_name VARCHAR(255)"))
        conn.commit()
    except Exception:
        pass


def extract_candidate_name(review: Review, parsed_dict: dict = None) -> str:
    if review.candidate_name and review.candidate_name.strip() and review.candidate_name != "Candidate":
        return review.candidate_name
    if parsed_dict is None:
        try:
            parsed_dict = json.loads(review.result_json)
        except Exception:
            parsed_dict = {}
    if parsed_dict.get("candidate_name") and parsed_dict["candidate_name"] != "Candidate":
        return parsed_dict["candidate_name"]
    candidate_info = parsed_dict.get("candidate_info", {})
    if isinstance(candidate_info, dict) and candidate_info.get("name") and candidate_info["name"] != "Candidate":
        return candidate_info["name"]
    personal = candidate_info.get("personal_details", []) if isinstance(candidate_info, dict) else []
    if not personal and isinstance(parsed_dict.get("personal_details"), list):
        personal = parsed_dict["personal_details"]
    if personal and len(personal) > 0:
        return personal[0]
    clean = re.sub(r"\.[^.]+$", "", review.filename or "Candidate")
    return clean.replace("_", " ").replace("-", " ").title()

app = FastAPI(
    title="AI Resume Reviewer API",
    description="FastAPI backend wrapping the local AI Resume Reviewer pipeline.",
    version="1.0.0",
)

# CORS setup for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global lock to serialize pipeline execution because it writes shared files in outputs/
# and requires chdir to repo root
pipeline_lock = threading.Lock()
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def check_ollama_reachable(host: str = "http://localhost:11434") -> bool:
    """Checks if the local Ollama instance is running and reachable."""
    try:
        r = httpx.get(f"{host}/api/version", timeout=3.0)
        return r.status_code == 200
    except Exception:
        return False


class OutputInterceptor:
    def __init__(self, callback, original_stdout):
        self.callback = callback
        self.original_stdout = original_stdout

    def write(self, text):
        self.original_stdout.write(text)
        self.original_stdout.flush()
        line = text.strip()
        if line and self.callback:
            self.callback(line)

    def flush(self):
        self.original_stdout.flush()


def execute_pipeline_sync(pdf_path: str, job_title: str, on_log=None) -> dict:
    """
    Executes run_pipeline under the global lock with cwd safely set to REPO_ROOT.
    Restores the previous working directory and stdout when finished.
    """
    with pipeline_lock:
        prev_cwd = os.getcwd()
        old_stdout = sys.stdout
        try:
            if on_log:
                sys.stdout = OutputInterceptor(on_log, old_stdout)
            os.chdir(REPO_ROOT)
            # Call run_pipeline strictly via keyword arguments to avoid positional argument mismatch
            return run_pipeline(pdf_path=pdf_path, job_title=job_title)
        finally:
            sys.stdout = old_stdout
            os.chdir(prev_cwd)


@app.get("/api/health")
def health_check():
    ollama_ok = check_ollama_reachable()
    return {
        "status": "online",
        "ollama_reachable": ollama_ok,
        "repo_root": str(REPO_ROOT),
    }


@app.post("/api/review")
async def review_resume(
    file: UploadFile = File(...),
    job_title: str = Form(...),
    force: bool = Form(False),
    stream: bool = Form(True),
    db: Session = Depends(get_db),
):
    clean_job_title = job_title.strip()
    if not clean_job_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job title is required."
        )

    # 1. Validate file extension
    filename = file.filename or "uploaded_resume.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted. Please upload a .pdf document."
        )

    # 2. Read and validate file size & magic bytes
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty."
        )
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 5 MB limit."
        )
    if not content.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file does not appear to be a valid PDF document (missing %PDF header)."
        )

    # 3. Compute SHA-256 hash
    file_hash = hashlib.sha256(content).hexdigest()

    # 4. Check database for existing review
    existing = (
        db.query(Review)
        .filter(Review.file_hash == file_hash, Review.job_title == clean_job_title)
        .first()
    )

    if existing and not force:
        try:
            parsed_result = json.loads(existing.result_json)
        except Exception:
            parsed_result = {}

        cached_payload = {
            "already_reviewed": True,
            "reviewed_at": existing.created_at.isoformat(),
            "id": existing.id,
            "file_hash": existing.file_hash,
            "filename": existing.filename,
            "candidate_name": extract_candidate_name(existing, parsed_result),
            "job_title": existing.job_title,
            "score": existing.score,
            "result": parsed_result,
        }

        if stream:
            from fastapi.responses import StreamingResponse

            async def cached_streamer():
                yield f"data: {json.dumps({'type': 'log', 'message': 'Loaded existing evaluation from database.'})}\n\n"
                yield f"data: {json.dumps({'type': 'result', 'data': cached_payload})}\n\n"

            return StreamingResponse(cached_streamer(), media_type="text/event-stream")

        return cached_payload

    # 5. Check if Ollama is available before launching the heavy pipeline
    if not check_ollama_reachable():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Ollama server is unreachable at http://localhost:11434. "
                "Please run 'ollama serve' in your terminal and verify the model is pulled."
            ),
        )

    if stream:
        from fastapi.responses import StreamingResponse

        async def stream_generator():
            log_queue = asyncio.Queue()
            loop = asyncio.get_running_loop()

            def push_log(line: str):
                if line.startswith("[0/4]"):
                    line = "[0/4] Parsing resume..."
                loop.call_soon_threadsafe(log_queue.put_nowait, line)

            temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            temp_path = Path(temp_file.name)
            temp_file.write(content)
            temp_file.flush()
            temp_file.close()

            async def pipeline_worker():
                try:
                    return await asyncio.to_thread(
                        execute_pipeline_sync, str(temp_path), clean_job_title, push_log
                    )
                except Exception as exc:
                    return exc

            worker_task = asyncio.create_task(pipeline_worker())

            while not worker_task.done() or not log_queue.empty():
                try:
                    line = await asyncio.wait_for(log_queue.get(), timeout=0.15)
                    yield f"data: {json.dumps({'type': 'log', 'message': line})}\n\n"
                except asyncio.TimeoutError:
                    continue

            result = await worker_task

            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass

            if isinstance(result, Exception):
                yield f"data: {json.dumps({'type': 'error', 'detail': f'Pipeline execution failed: {str(result)}'})}\n\n"
                return

            score_val = int(result.get("score", 0))
            now = datetime.now(timezone.utc)
            cand_name = result.get("candidate_name") or extract_candidate_name(Review(filename=filename), result)
            if existing:
                existing.filename = filename
                existing.candidate_name = cand_name
                existing.result_json = json.dumps(result, ensure_ascii=False)
                existing.score = score_val
                existing.created_at = now
                review_record = existing
            else:
                review_record = Review(
                    file_hash=file_hash,
                    filename=filename,
                    candidate_name=cand_name,
                    job_title=clean_job_title,
                    result_json=json.dumps(result, ensure_ascii=False),
                    score=score_val,
                    created_at=now,
                )
                db.add(review_record)

            db.commit()
            db.refresh(review_record)

            response_data = {
                "already_reviewed": False,
                "reviewed_at": review_record.created_at.isoformat(),
                "id": review_record.id,
                "file_hash": review_record.file_hash,
                "filename": review_record.filename,
                "candidate_name": review_record.candidate_name or cand_name,
                "job_title": review_record.job_title,
                "score": review_record.score,
                "result": result,
            }
            yield f"data: {json.dumps({'type': 'result', 'data': response_data})}\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    # Non-streaming fallback
    temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    temp_path = Path(temp_file.name)
    try:
        temp_file.write(content)
        temp_file.flush()
        temp_file.close()

        pipeline_result = await asyncio.to_thread(
            execute_pipeline_sync, str(temp_path), clean_job_title
        )
        score_val = int(pipeline_result.get("score", 0))
        now = datetime.now(timezone.utc)
        cand_name = pipeline_result.get("candidate_name") or extract_candidate_name(Review(filename=filename), pipeline_result)
        if existing:
            existing.filename = filename
            existing.candidate_name = cand_name
            existing.result_json = json.dumps(pipeline_result, ensure_ascii=False)
            existing.score = score_val
            existing.created_at = now
            review_record = existing
        else:
            review_record = Review(
                file_hash=file_hash,
                filename=filename,
                candidate_name=cand_name,
                job_title=clean_job_title,
                result_json=json.dumps(pipeline_result, ensure_ascii=False),
                score=score_val,
                created_at=now,
            )
            db.add(review_record)

        db.commit()
        db.refresh(review_record)

        return {
            "already_reviewed": False,
            "reviewed_at": review_record.created_at.isoformat(),
            "id": review_record.id,
            "file_hash": review_record.file_hash,
            "filename": review_record.filename,
            "candidate_name": review_record.candidate_name or cand_name,
            "job_title": review_record.job_title,
            "score": review_record.score,
            "result": pipeline_result,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution failed: {str(exc)}"
        )
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass


@app.get("/api/reviews")
def list_reviews(
    q: str | None = Query(None, description="Search term for filename or job_title"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    size: int | None = Query(None, description="Alias for page_size"),
    db: Session = Depends(get_db),
):
    effective_size = size if size is not None else page_size
    query = db.query(Review)
    if q and q.strip():
        search_filter = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Review.filename.ilike(search_filter),
                Review.job_title.ilike(search_filter),
                Review.candidate_name.ilike(search_filter),
                Review.result_json.ilike(search_filter),
            )
        )

    total = query.count()
    items = (
        query.order_by(Review.created_at.desc())
        .offset((page - 1) * effective_size)
        .limit(effective_size)
        .all()
    )

    total_pages = math.ceil(total / effective_size) if total > 0 else 1

    serialized_reviews = [
        {
            "id": r.id,
            "file_hash": r.file_hash,
            "filename": r.filename,
            "candidate_name": extract_candidate_name(r),
            "job_title": r.job_title,
            "score": r.score,
            "created_at": r.created_at.isoformat(),
        }
        for r in items
    ]

    return {
        "items": serialized_reviews,
        "reviews": serialized_reviews,
        "total": total,
        "page": page,
        "size": effective_size,
        "page_size": effective_size,
        "pages": total_pages,
        "total_pages": total_pages,
    }


@app.get("/api/reviews/{review_id}")
def get_review(review_id: int, db: Session = Depends(get_db)):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review with id {review_id} not found."
        )

    try:
        parsed_result = json.loads(review.result_json)
    except Exception:
        parsed_result = {}

    return {
        "id": review.id,
        "file_hash": review.file_hash,
        "filename": review.filename,
        "candidate_name": extract_candidate_name(review, parsed_result),
        "job_title": review.job_title,
        "score": review.score,
        "created_at": review.created_at.isoformat(),
        "result": parsed_result,
    }


@app.delete("/api/reviews/{review_id}")
def delete_review(review_id: int, db: Session = Depends(get_db)):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review with id {review_id} not found."
        )

    db.delete(review)
    db.commit()
    return {"success": True, "message": f"Review {review_id} deleted successfully."}
