"""REST API for managing scheduled actions."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.schedule import ScheduledAction, ScheduledRun

router = APIRouter()


class ScheduleCreate(BaseModel):
    name: str
    cron_expression: str
    prompt: str
    enabled: bool = True


class ScheduleUpdate(BaseModel):
    name: str | None = None
    cron_expression: str | None = None
    prompt: str | None = None
    enabled: bool | None = None


# --- Built-in templates ---

TEMPLATES = [
    {
        "name": "Morning Briefing",
        "cron_expression": "0 7 * * *",
        "prompt": "Give me a morning briefing: summarize today's calendar events, list any unread important emails, and check for stale GitHub project items.",
    },
    {
        "name": "Daily Summary",
        "cron_expression": "0 22 * * *",
        "prompt": "Write a daily summary to notes/daily/ with today's date. Include what calendar events happened, any emails sent/received, and notes taken today.",
    },
    {
        "name": "Inbox Triage",
        "cron_expression": "0 */2 * * *",
        "prompt": "Check for new unread emails. Summarize any that look important or time-sensitive.",
    },
]


@router.get("/")
async def list_schedules(session: Session = Depends(get_session)):
    actions = session.exec(
        select(ScheduledAction).order_by(ScheduledAction.created_at)  # type: ignore
    ).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "cron_expression": a.cron_expression,
            "prompt": a.prompt,
            "enabled": a.enabled,
            "created_at": a.created_at.isoformat(),
        }
        for a in actions
    ]


@router.post("/")
async def create_schedule(body: ScheduleCreate, session: Session = Depends(get_session)):
    action = ScheduledAction(
        name=body.name,
        cron_expression=body.cron_expression,
        prompt=body.prompt,
        enabled=body.enabled,
    )
    session.add(action)
    session.commit()
    session.refresh(action)
    return {"id": action.id, "status": "created"}


@router.patch("/{schedule_id}")
async def update_schedule(
    schedule_id: int, body: ScheduleUpdate, session: Session = Depends(get_session)
):
    action = session.get(ScheduledAction, schedule_id)
    if not action:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if body.name is not None:
        action.name = body.name
    if body.cron_expression is not None:
        action.cron_expression = body.cron_expression
    if body.prompt is not None:
        action.prompt = body.prompt
    if body.enabled is not None:
        action.enabled = body.enabled

    action.updated_at = datetime.now(timezone.utc)
    session.add(action)
    session.commit()
    return {"id": action.id, "status": "updated"}


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: int, session: Session = Depends(get_session)):
    action = session.get(ScheduledAction, schedule_id)
    if not action:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Delete associated runs
    runs = session.exec(
        select(ScheduledRun).where(ScheduledRun.action_id == schedule_id)
    ).all()
    for run in runs:
        session.delete(run)

    session.delete(action)
    session.commit()
    return {"status": "deleted"}


@router.get("/{schedule_id}/runs")
async def list_schedule_runs(
    schedule_id: int, limit: int = 20, session: Session = Depends(get_session)
):
    runs = session.exec(
        select(ScheduledRun)
        .where(ScheduledRun.action_id == schedule_id)
        .order_by(ScheduledRun.started_at.desc())  # type: ignore
        .limit(limit)
    ).all()
    return [
        {
            "id": r.id,
            "started_at": r.started_at.isoformat(),
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "status": r.status,
            "result": r.result[:200] if r.result else "",
            "error": r.error,
        }
        for r in runs
    ]


@router.get("/templates")
async def list_templates():
    """Return built-in schedule templates."""
    return TEMPLATES
