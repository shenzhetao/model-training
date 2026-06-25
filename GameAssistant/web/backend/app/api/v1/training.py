"""Training management API — create, monitor, and stream training jobs."""
import asyncio
import json
import os
import signal
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.security import get_current_user
from app.schemas.training import (
    TrainingJobCreate, TrainingJobUpdate, TrainingJobResponse,
    TrainingLogResponse, TrainingProgressResponse,
)
from app.crud.training import training_job_crud, training_log_crud, TrainingHelper
from app.crud.dataset import dataset_version_crud
from app.config import settings

router = APIRouter()


# ── Training Job routes ─────────────────────────────────────

@router.get("/", response_model=list[TrainingJobResponse])
async def list_training_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    dataset_version_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List training jobs."""
    skip = (page - 1) * page_size
    jobs, total = await training_job_crud.get_multi_paginated(
        db, skip=skip, limit=page_size,
        status=status, dataset_version_id=dataset_version_id,
    )
    return jobs


@router.post("/", response_model=TrainingJobResponse)
async def create_training_job(
    obj_in: TrainingJobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new training job and launch it in background."""
    from app.models.dataset import DatasetVersion

    version: DatasetVersion = await dataset_version_crud.get(db, obj_in.dataset_version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Dataset version not found")
    if version.status != "ready":
        raise HTTPException(status_code=400, detail="Dataset version is not ready. Generate YOLO dataset first.")

    job_data = {
        **obj_in.model_dump(),
        "created_by": current_user.id,
        "status": "pending",
    }
    job = await training_job_crud.create(db, job_data)
    await db.commit()

    background_tasks.add_task(_run_training, job.id, current_user.id)

    return job


async def _run_training(job_id: str, user_id: str):
    """Background task that runs YOLO training."""
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        job = await training_job_crud.get(db, job_id)
        if not job:
            return

        await training_job_crud.start_training(db, job_id)
        await db.commit()

        version = await dataset_version_crud.get(db, job.dataset_version_id)
        if not version or not version.yolo_dataset_path:
            await db.execute(
                f"UPDATE training_jobs SET status='failed', error_message='No YOLO dataset found' WHERE id='{job_id}'"
            )
            await db.commit()
            return

        yaml_content = version.dataset_yaml_content or "path: .\ntrain: train/images\nval: val/images\nnames:\n  - class_0\n"
        yaml_dir = os.path.join(settings.MODEL_DIR, "datasets")
        os.makedirs(yaml_dir, exist_ok=True)
        yaml_path = os.path.join(yaml_dir, f"{job_id}.yaml")
        with open(yaml_path, "w") as f:
            f.write(yaml_content)

        output_dir = os.path.join(settings.MODEL_DIR, "runs", "train")
        os.makedirs(output_dir, exist_ok=True)

        cmd = TrainingHelper.build_command(job, yaml_path, output_dir)
        log_lines: list[str] = []

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=settings.BASE_DIR,
            )

            await db.execute(
                f"UPDATE training_jobs SET process_id={proc.pid} WHERE id='{job_id}'"
            )
            await db.commit()

            async for line in proc.stdout:
                decoded = line.decode("utf-8", errors="replace").strip()
                if decoded:
                    log_lines.append(decoded)
                    await _parse_and_log_epoch(db, job_id, decoded)

            await proc.wait()

            if proc.returncode == 0:
                best_weights = os.path.join(output_dir, job_id, "weights", "best.pt")
                if os.path.exists(best_weights):
                    from app.crud.model import _save_model_file, model_crud
                    with open(best_weights, "rb") as f:
                        content = f.read()
                    model_path = _save_model_file(content, f"best_{job_id}.pt")

                    model_data = {
                        "name": f"{job.name} (best)",
                        "architecture": job.base_model_architecture,
                        "dataset_version_id": job.dataset_version_id,
                        "training_job_id": job.id,
                        "file_path": model_path,
                        "file_size": len(content),
                        "epochs": job.epochs,
                        "img_size": job.img_size,
                        "batch_size": job.batch_size,
                    }
                    new_model = await model_crud.create(db, model_data)
                    await db.execute(
                        f"UPDATE training_jobs SET status='completed', best_model_id='{new_model.id}', completed_at=NOW() WHERE id='{job_id}'"
                    )
                else:
                    await db.execute(
                        f"UPDATE training_jobs SET status='completed', completed_at=NOW() WHERE id='{job_id}'"
                    )
            else:
                await db.execute(
                    f"UPDATE training_jobs SET status='failed', error_message='Training process exited with code {proc.returncode}' WHERE id='{job_id}'"
                )

            full_log = "\n".join(log_lines[-2000:])
            await db.execute(
                f"UPDATE training_jobs SET log_output='{full_log.replace(chr(39), chr(39)+chr(39))}' WHERE id='{job_id}'"
            )
            await db.commit()

        except FileNotFoundError:
            await db.execute(
                f"UPDATE training_jobs SET status='failed', error_message='ultralytics not installed. Run: pip install ultralytics' WHERE id='{job_id}'"
            )
            await db.commit()
        except Exception as e:
            await db.execute(
                f"UPDATE training_jobs SET status='failed', error_message='{str(e).replace(chr(39), chr(39)+chr(39))}' WHERE id='{job_id}'"
            )
            await db.commit()


async def _parse_and_log_epoch(db: AsyncSession, job_id: str, line: str):
    """Parse epoch info from YOLO log line and save to training_logs."""
    import re
    epoch_match = re.search(r"epoch\s+(\d+)", line)
    if not epoch_match:
        return

    epoch = int(epoch_match.group(1))

    metrics: dict = {}
    for key in ["box", "cls", "dfl"]:
        m = re.search(rf"{key}_loss[= ]+([0-9.]+)", line)
        if m:
            metrics[f"train_{key}_loss"] = float(m.group(1))
        m2 = re.search(rf"val[._]{key}_loss[= ]+([0-9.]+)", line)
        if m2:
            metrics[f"val_{key}_loss"] = float(m2.group(1))

    for key in ["precision", "recall", "mAP50", "mAP50-95"]:
        m = re.search(rf"{key}[= ]+([0-9.]+)", line)
        if m:
            if key == "mAP50":
                metrics["map50"] = float(m.group(1))
            elif key == "mAP50-95":
                metrics["map50_95"] = float(m.group(1))
            else:
                metrics[key] = float(m.group(1))

    lr_match = re.search(r"lr[=: ]+([0-9.e-]+)", line)
    if lr_match:
        metrics["lr"] = float(lr_match.group(1))

    if metrics:
        from app.models.training import TrainingLog
        import uuid
        log = TrainingLog(
            id=str(uuid.uuid4()),
            training_job_id=job_id,
            epoch=epoch,
            train_box_loss=metrics.get("train_box_loss"),
            train_cls_loss=metrics.get("train_cls_loss"),
            train_dfl_loss=metrics.get("train_dfl_loss"),
            val_box_loss=metrics.get("val_box_loss"),
            val_cls_loss=metrics.get("val_cls_loss"),
            val_dfl_loss=metrics.get("val_dfl_loss"),
            precision=metrics.get("precision"),
            recall=metrics.get("recall"),
            map50=metrics.get("map50"),
            map50_95=metrics.get("map50_95"),
            lr=metrics.get("lr"),
        )
        db.add(log)
        await db.flush()


@router.get("/{job_id}", response_model=TrainingJobResponse)
async def get_training_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get training job details."""
    job = await training_job_crud.get(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    return job


@router.put("/{job_id}", response_model=TrainingJobResponse)
async def update_training_job(
    job_id: str,
    obj_in: TrainingJobUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update training job (e.g. stop, rename)."""
    job = await training_job_crud.get(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")

    update_data = obj_in.model_dump(exclude_unset=True)
    if obj_in.status == "cancelled" and job.status == "running":
        if job.process_id:
            try:
                os.kill(job.process_id, signal.SIGTERM)
            except OSError:
                pass
        update_data["completed_at"] = datetime.utcnow()

    updated = await training_job_crud.update(db, job_id, update_data)
    await db.commit()
    return updated


@router.post("/{job_id}/stop")
async def stop_training_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stop a running training job."""
    job = await training_job_crud.get(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    if job.status != "running":
        raise HTTPException(status_code=400, detail="Job is not running")

    if job.process_id:
        try:
            os.kill(job.process_id, signal.SIGTERM)
        except OSError:
            pass

    updated = await training_job_crud.update(db, job_id, {
        "status": "cancelled",
        "completed_at": datetime.utcnow(),
    })
    await db.commit()
    return {"success": True, "message": "Training job stopped"}


@router.get("/{job_id}/logs")
async def stream_training_logs(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SSE stream of training logs for a job."""
    job = await training_job_crud.get(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")

    async def event_generator():
        last_epoch = 0
        while True:
            await asyncio.sleep(3)
            async with db.begin():
                latest = await training_log_crud.get_latest(db, job_id)
                job_ref = await training_job_crud.get(db, job_id)

            if not job_ref or job_ref.status in ("completed", "failed", "cancelled"):
                yield f"data: {json.dumps({'type': 'done', 'status': job_ref.status if job_ref else 'unknown'})}\n\n"
                break

            if latest and latest.epoch > last_epoch:
                last_epoch = latest.epoch
                yield f"data: {json.dumps({'type': 'epoch', **TrainingLogResponse.model_validate(latest).model_dump()})}\n\n"

            yield f"data: {json.dumps({'type': 'heartbeat', 'epoch': last_epoch, 'status': job_ref.status})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{job_id}/metrics", response_model=list[TrainingLogResponse])
async def get_training_metrics(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all epoch metrics for a training job."""
    job = await training_job_crud.get(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    return await training_log_crud.get_by_job(db, job_id)


@router.get("/{job_id}/progress", response_model=TrainingProgressResponse)
async def get_training_progress(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current training progress summary."""
    job = await training_job_crud.get(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")

    latest = await training_log_crud.get_latest(db, job_id)

    return TrainingProgressResponse(
        job_id=job_id,
        status=job.status,
        current_epoch=job.current_epoch or 0,
        total_epochs=job.epochs,
        best_model_id=job.best_model_id,
        current_map50=latest.map50 if latest else None,
        current_map=latest.map50_95 if latest else None,
        latest_metrics=TrainingLogResponse.model_validate(latest) if latest else None,
    )
