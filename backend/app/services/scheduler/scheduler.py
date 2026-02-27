"""Background scheduler that runs scheduled actions via cron expressions."""

import asyncio
import logging
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.core.database import engine
from app.models.schedule import ScheduledAction, ScheduledRun
from app.services.agent import Agent

logger = logging.getLogger(__name__)

# Rate limit: max scheduled runs per hour
MAX_RUNS_PER_HOUR = 30


def _cron_matches_now(cron_expr: str, now: datetime) -> bool:
    """Simple cron matcher for: minute hour day_of_month month day_of_week.

    Supports * (any) and specific values. Does not support ranges or steps.
    """
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        return False

    fields = [
        (parts[0], now.minute),
        (parts[1], now.hour),
        (parts[2], now.day),
        (parts[3], now.month),
        (parts[4], now.isoweekday() % 7),  # 0=Sun
    ]

    for pattern, value in fields:
        if pattern == "*":
            continue
        try:
            if "," in pattern:
                if value not in [int(p) for p in pattern.split(",")]:
                    return False
            elif int(pattern) != value:
                return False
        except ValueError:
            return False

    return True


def _count_recent_runs(session: Session, hours: int = 1) -> int:
    """Count runs in the last N hours for rate limiting."""
    cutoff = datetime.now(timezone.utc).replace(
        minute=0, second=0, microsecond=0
    )
    runs = session.exec(
        select(ScheduledRun).where(ScheduledRun.started_at >= cutoff)
    ).all()
    return len(runs)


async def _execute_scheduled_action(action: ScheduledAction) -> None:
    """Execute a scheduled action through the agent."""
    run = ScheduledRun(action_id=action.id)  # type: ignore
    with Session(engine) as session:
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    agent = Agent()
    messages = [{"role": "user", "parts": [{"text": action.prompt}]}]

    try:
        full_response = ""
        async for token in agent.run(messages):
            full_response += token

        with Session(engine) as session:
            run = session.get(ScheduledRun, run_id)
            if run:
                run.status = "success"
                run.result = full_response[:5000]  # Truncate if very long
                run.finished_at = datetime.now(timezone.utc)
                session.add(run)
                session.commit()

        logger.info(f"Scheduled action '{action.name}' completed successfully")

    except Exception as e:
        logger.error(f"Scheduled action '{action.name}' failed: {e}")
        with Session(engine) as session:
            run = session.get(ScheduledRun, run_id)
            if run:
                run.status = "failed"
                run.error = str(e)[:1000]
                run.finished_at = datetime.now(timezone.utc)
                session.add(run)
                session.commit()


async def _check_weekly_summary(now: datetime) -> None:
    """Run weekly summary generation on Monday at 01:00 UTC."""
    if now.weekday() == 0 and now.hour == 1 and now.minute == 0:
        logger.info("Triggering weekly summary generation")
        try:
            from app.services.drive_sync import generate_weekly_summary

            await generate_weekly_summary()
        except Exception:
            logger.exception("Weekly summary generation failed")


async def scheduler_loop() -> None:
    """Main scheduler loop. Checks every 60 seconds for actions to run."""
    logger.info("Scheduler started")

    while True:
        try:
            now = datetime.now(timezone.utc)

            # Weekly summary check (Monday 01:00 UTC)
            await _check_weekly_summary(now)

            with Session(engine) as session:
                # Rate limit check
                recent_count = _count_recent_runs(session)
                if recent_count >= MAX_RUNS_PER_HOUR:
                    logger.warning(f"Rate limit reached ({recent_count} runs this hour), skipping")
                    await asyncio.sleep(60)
                    continue

                # Get enabled actions
                actions = session.exec(
                    select(ScheduledAction).where(ScheduledAction.enabled == True)  # noqa: E712
                ).all()

            for action in actions:
                if _cron_matches_now(action.cron_expression, now):
                    logger.info(f"Running scheduled action: {action.name}")
                    # Run in background so we don't block the scheduler
                    asyncio.create_task(_execute_scheduled_action(action))

        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        # Sleep until next minute
        await asyncio.sleep(60)
