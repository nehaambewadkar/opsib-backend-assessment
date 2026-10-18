
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import ExceptionRecord, TaskRecord
from app.workflows.task_workflow import transition_task_status


app = FastAPI(
    title="OPSiB Backend Assessment",
    description="Retail data integration and exception management API",
    version="1.0.0",
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TaskStatusUpdate(BaseModel):
    new_status: str
    actor_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)


@app.get("/")
def home():
    return {
        "message": "OPSiB Backend API is running",
        "status": "healthy",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/exceptions")
def list_exceptions(db: Session = Depends(get_db)):
    exceptions = (
        db.query(ExceptionRecord)
        .order_by(ExceptionRecord.id)
        .all()
    )

    return [
        {
            "id": item.id,
            "exception_key": item.exception_key,
            "po_number": item.po_number,
            "line_number": item.line_number,
            "location_id": item.location_id,
            "product_id": item.product_id,
            "ordered_qty": str(item.ordered_qty),
            "accepted_qty": str(item.accepted_qty),
            "shortfall_qty": str(item.shortfall_qty),
            "base_uom": item.base_uom,
            "reason": item.reason,
            "status": item.status,
        }
        for item in exceptions
    ]


@app.get("/tasks")
def list_tasks(db: Session = Depends(get_db)):
    tasks = db.query(TaskRecord).order_by(TaskRecord.id).all()

    return [
        {
            "id": item.id,
            "task_key": item.task_key,
            "exception_id": item.exception_id,
            "assignee_id": item.assignee_id,
            "assignee_role": item.assignee_role,
            "assignment_reason": item.assignment_reason,
            "status": item.status,
        }
        for item in tasks
    ]


@app.get("/tasks/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(TaskRecord, task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "id": task.id,
        "task_key": task.task_key,
        "exception_id": task.exception_id,
        "assignee_id": task.assignee_id,
        "assignee_role": task.assignee_role,
        "assignment_reason": task.assignment_reason,
        "status": task.status,
    }


@app.patch("/tasks/{task_id}/status")
def update_task_status(
    task_id: int,
    payload: TaskStatusUpdate,
    db: Session = Depends(get_db),
):
    try:
        task = transition_task_status(
            db=db,
            task_id=task_id,
            new_status=payload.new_status,
            actor_id=payload.actor_id,
            reason=payload.reason,
        )
        db.commit()
        db.refresh(task)

        return {
            "message": "Task status updated successfully",
            "task_id": task.id,
            "status": task.status,
        }

    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except Exception:
        db.rollback()
        raise
