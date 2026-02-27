"""REST API for workout logs and routine management."""

import json
import re
import uuid
from datetime import date as _date, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.sandbox import SandboxError, resolve_sandboxed_path

router = APIRouter()

LOGS_DIR = "workouts"
ROUTINES_DIR = "workouts/routines"


# ── Pydantic models ───────────────────────────────────────────────────────────

class Progression(BaseModel):
    name: str
    description: str = ""


class Exercise(BaseModel):
    id: str
    name: str
    type: str  # warmup | strength | cooldown
    repRange: str = ""
    notes: str = ""
    defaultSets: int = 1
    wikiUrl: str = ""
    progressions: list[Progression] = []


class WorkoutSection(BaseModel):
    name: str
    type: str
    exercises: list[Exercise] = []


class Routine(BaseModel):
    id: str
    name: str
    description: str = ""
    builtin: bool = False
    sections: list[WorkoutSection] = []


class SetLog(BaseModel):
    reps: str = ""
    weight: str = ""


class ExerciseLog(BaseModel):
    exerciseId: str
    progressionLevel: int = 0
    sets: list[SetLog] = []
    done: bool = False


class WorkoutLog(BaseModel):
    date: str
    routineId: str
    exercises: dict[str, ExerciseLog] = {}


# ── Default BWF Recommended Routine ──────────────────────────────────────────

_BWF_RR: dict = {
    "id": "bwf-rr",
    "name": "BWF Recommended Routine",
    "description": (
        "A balanced bodyweight strength program. "
        "3 sessions per week covering push, pull, and legs."
    ),
    "builtin": True,
    "sections": [
        {
            "name": "Warm-up",
            "type": "warmup",
            "exercises": [
                {
                    "id": "yuris-warmup",
                    "name": "Yuri's Shoulder Band Warmup",
                    "type": "warmup",
                    "repRange": "5-10",
                    "notes": "Less good: Stick dislocates, can also be done with a tee-shirt",
                    "defaultSets": 1,
                    "wikiUrl": "",
                    "progressions": [
                        {
                            "name": "Yuri's Shoulder Band Warmup",
                            "description": (
                                "Loop a resistance band overhead. "
                                "Keeping arms straight, bring the band from front to back "
                                "overhead in a smooth arc. Reverse."
                            ),
                        }
                    ],
                },
                {
                    "id": "squat-sky-reaches",
                    "name": "Squat Sky Reaches",
                    "type": "warmup",
                    "repRange": "5-10",
                    "notes": "You can do these assisted.",
                    "defaultSets": 1,
                    "wikiUrl": "",
                    "progressions": [
                        {
                            "name": "Squat Sky Reaches",
                            "description": (
                                "Squat down and touch the floor, "
                                "then stand and reach both arms overhead. "
                                "Can hold a pole or TRX for assistance."
                            ),
                        }
                    ],
                },
                {
                    "id": "gmb-wrist-prep",
                    "name": "GMB Wrist Prep",
                    "type": "warmup",
                    "repRange": "10+",
                    "notes": "",
                    "defaultSets": 1,
                    "wikiUrl": "",
                    "progressions": [
                        {
                            "name": "GMB Wrist Prep",
                            "description": (
                                "Series of wrist circles, extensions, and loaded weight shifts. "
                                "Do as many reps as you want — focus on wrist health."
                            ),
                        }
                    ],
                },
                {
                    "id": "deadbugs",
                    "name": "Deadbugs",
                    "type": "warmup",
                    "repRange": "30s",
                    "notes": "",
                    "defaultSets": 1,
                    "wikiUrl": "",
                    "progressions": [
                        {
                            "name": "Deadbugs",
                            "description": (
                                "Lie on back, arms pointing up, knees at 90°. "
                                "Lower opposite arm and leg simultaneously while keeping "
                                "lower back pressed to floor. Return and alternate."
                            ),
                        }
                    ],
                },
                {
                    "id": "arch-hangs",
                    "name": "Arch Hangs",
                    "type": "warmup",
                    "repRange": "10",
                    "notes": "Add these after you reach Negative Pullups.",
                    "defaultSets": 1,
                    "wikiUrl": "",
                    "progressions": [
                        {
                            "name": "Arch Hang",
                            "description": (
                                "From a dead hang, retract scapulae and arch back slightly, "
                                "pushing chest forward. Hold briefly then return to dead hang."
                            ),
                        }
                    ],
                },
                {
                    "id": "support-hold",
                    "name": "Support Hold",
                    "type": "warmup",
                    "repRange": "30s",
                    "notes": "Add these after you reach Negative Dips.",
                    "defaultSets": 1,
                    "wikiUrl": "",
                    "progressions": [
                        {
                            "name": "Support Hold",
                            "description": (
                                "On parallel bars or two sturdy chairs, "
                                "support your full weight with straight arms. "
                                "Hold the top dip position for the prescribed time."
                            ),
                        }
                    ],
                },
                {
                    "id": "warmup-squat",
                    "name": "Easier Squat Progression",
                    "type": "warmup",
                    "repRange": "10",
                    "notes": "Add these after you reach Bulgarian Split Squats.",
                    "defaultSets": 1,
                    "wikiUrl": "",
                    "progressions": [
                        {
                            "name": "Assisted Squat",
                            "description": (
                                "Hold a pole or TRX for balance. "
                                "Focus on depth and keeping heels on floor."
                            ),
                        },
                        {
                            "name": "Bodyweight Squat",
                            "description": (
                                "Full depth squat with bodyweight. "
                                "Feet shoulder-width, toes slightly out."
                            ),
                        },
                        {
                            "name": "Narrow Squat",
                            "description": "Feet closer together — increases mobility demand.",
                        },
                    ],
                },
                {
                    "id": "warmup-hinge",
                    "name": "Easier Hinge Progression",
                    "type": "warmup",
                    "repRange": "10",
                    "notes": "Add these after you reach Banded Nordic Curls.",
                    "defaultSets": 1,
                    "wikiUrl": "",
                    "progressions": [
                        {
                            "name": "Romanian Deadlift",
                            "description": (
                                "Stand tall, hinge at hips keeping back flat. "
                                "Lower hands toward floor, feel hamstring stretch, return."
                            ),
                        },
                        {
                            "name": "Single-Leg RDL",
                            "description": (
                                "Same as RDL but balance on one leg, "
                                "other extends behind as counterbalance."
                            ),
                        },
                    ],
                },
            ],
        },
        {
            "name": "Strength",
            "type": "strength",
            "exercises": [
                {
                    "id": "pullup",
                    "name": "Pull-up Progression",
                    "type": "strength",
                    "repRange": "5-8",
                    "notes": "Pair 1 — superset with Dip Progression",
                    "defaultSets": 3,
                    "wikiUrl": "https://www.reddit.com/r/bodyweightfitness/wiki/exercises/pullup",
                    "progressions": [
                        {"name": "Dead Hang", "description": "Hang from bar with arms fully extended. Build grip and scapular strength."},
                        {"name": "Scapular Pull-ups", "description": "From dead hang, retract scapulae to lift body slightly without bending elbows."},
                        {"name": "Negative Pull-ups", "description": "Jump or step to top position, lower yourself slowly over 3-5 seconds."},
                        {"name": "Assisted Pull-ups", "description": "Use resistance band or foot on chair to reduce load. Full range of motion."},
                        {"name": "Jumping Pull-ups", "description": "Use legs to help initiate movement, control the negative."},
                        {"name": "Pull-ups", "description": "Full pull-up from dead hang to chin over bar."},
                        {"name": "Chin-ups", "description": "Supinated grip (palms facing you) pull-up. Often easier for beginners."},
                        {"name": "Weighted Pull-ups", "description": "Add weight via belt, vest, or hold dumbbell between feet."},
                    ],
                },
                {
                    "id": "dip",
                    "name": "Dip Progression",
                    "type": "strength",
                    "repRange": "5-8",
                    "notes": "Pair 1 — superset with Pull-up Progression",
                    "defaultSets": 3,
                    "wikiUrl": "https://www.reddit.com/r/bodyweightfitness/wiki/exercises/dip",
                    "progressions": [
                        {"name": "Bench Dips", "description": "Hands on bench behind you, feet on floor. Bend elbows to lower hips."},
                        {"name": "Negative Dips", "description": "Jump to top of parallel bars, lower slowly over 3-5 seconds."},
                        {"name": "Assisted Dips", "description": "Use resistance band or foot support to reduce load."},
                        {"name": "Parallel Bar Dips", "description": "Full dip on parallel bars. Lower until elbows reach ~90°, then press up."},
                        {"name": "Ring Dips", "description": "Dips on gymnastic rings — requires significant stabilization."},
                        {"name": "Weighted Dips", "description": "Add weight via belt, vest, or hold dumbbell between feet."},
                    ],
                },
                {
                    "id": "squat",
                    "name": "Squat Progression",
                    "type": "strength",
                    "repRange": "5-8",
                    "notes": "Pair 2 — superset with Hip Hinge Progression",
                    "defaultSets": 3,
                    "wikiUrl": "https://www.reddit.com/r/bodyweightfitness/wiki/exercises/squat",
                    "progressions": [
                        {"name": "Assisted Squat", "description": "Hold a pole or TRX for balance. Work on full depth."},
                        {"name": "Bodyweight Squat", "description": "Full depth squat. Feet shoulder-width, toes slightly out."},
                        {"name": "Split Squat", "description": "Stationary lunge position. Lower back knee toward floor."},
                        {"name": "Bulgarian Split Squat", "description": "Rear foot elevated on bench. Deep lunge movement."},
                        {"name": "Shrimp Squat Progression", "description": "Single-leg squat holding back foot. Work toward full depth."},
                        {"name": "Pistol Squat", "description": "Single-leg squat to full depth with other leg extended forward."},
                    ],
                },
                {
                    "id": "hinge",
                    "name": "Hip Hinge Progression",
                    "type": "strength",
                    "repRange": "5-8",
                    "notes": "Pair 2 — superset with Squat Progression",
                    "defaultSets": 3,
                    "wikiUrl": "https://www.reddit.com/r/bodyweightfitness/wiki/exercises/hinge",
                    "progressions": [
                        {"name": "Romanian Deadlift", "description": "Hip hinge keeping back flat. Feel hamstring stretch at bottom."},
                        {"name": "Single-Leg RDL", "description": "Balance on one leg while hinging. Use arms for counterbalance."},
                        {"name": "Banded Nordic Curl", "description": "Anchor feet, use band for assistance. Lower torso toward floor."},
                        {"name": "Negative Nordic Curl", "description": "Lower slowly without band. Use hands to push back up."},
                        {"name": "Nordic Curl", "description": "Full Nordic hamstring curl. Anchor feet, lower chest to floor under control."},
                    ],
                },
                {
                    "id": "row",
                    "name": "Row Progression",
                    "type": "strength",
                    "repRange": "5-8",
                    "notes": "Pair 3 — superset with Push-up Progression",
                    "defaultSets": 3,
                    "wikiUrl": "https://www.reddit.com/r/bodyweightfitness/wiki/exercises/row",
                    "progressions": [
                        {"name": "Incline Row", "description": "Body at 45° angle. Pull chest to bar."},
                        {"name": "Horizontal Row", "description": "Body parallel to floor. Pull chest to bar or rings."},
                        {"name": "Wide Row", "description": "Wider grip row. More lat involvement."},
                        {"name": "Tuck Front Lever Row", "description": "Row from tuck front lever position. Advanced."},
                        {"name": "Archer Row", "description": "One arm pulls while other extends. Builds toward one-arm row."},
                    ],
                },
                {
                    "id": "pushup",
                    "name": "Push-up Progression",
                    "type": "strength",
                    "repRange": "5-8",
                    "notes": "Pair 3 — superset with Row Progression",
                    "defaultSets": 3,
                    "wikiUrl": "https://www.reddit.com/r/bodyweightfitness/wiki/exercises/pushup",
                    "progressions": [
                        {"name": "Incline Push-up", "description": "Hands elevated on surface. Reduces load."},
                        {"name": "Push-up", "description": "Standard push-up. Hands shoulder-width, full range of motion."},
                        {"name": "Diamond Push-up", "description": "Hands close together. More tricep focus."},
                        {"name": "Pike Push-up", "description": "Hips high in inverted V. Targets shoulders for HSPU progression."},
                        {"name": "Pseudo Planche Push-up", "description": "Hands by hips, fingers pointing back, lean forward."},
                        {"name": "Archer Push-up", "description": "One arm extended to side while other bends. Unilateral builder."},
                    ],
                },
            ],
        },
        {
            "name": "Cool-down",
            "type": "cooldown",
            "exercises": [
                {
                    "id": "wrist-stretch",
                    "name": "Wrist Stretch",
                    "type": "cooldown",
                    "repRange": "30s each",
                    "notes": "",
                    "defaultSets": 1,
                    "wikiUrl": "",
                    "progressions": [
                        {"name": "Wrist Extension", "description": "Extend one arm, use other hand to pull fingers back gently. Hold 30s each side."},
                    ],
                },
                {
                    "id": "chest-stretch",
                    "name": "Chest Stretch",
                    "type": "cooldown",
                    "repRange": "30-60s",
                    "notes": "",
                    "defaultSets": 1,
                    "wikiUrl": "",
                    "progressions": [
                        {"name": "Doorway Stretch", "description": "Stand in doorway with arms at 90°. Lean forward to stretch chest and anterior shoulder."},
                    ],
                },
                {
                    "id": "hip-flexor",
                    "name": "Hip Flexor Stretch",
                    "type": "cooldown",
                    "repRange": "30s each",
                    "notes": "",
                    "defaultSets": 1,
                    "wikiUrl": "",
                    "progressions": [
                        {"name": "Kneeling Lunge Stretch", "description": "One knee on floor, other foot forward at 90°. Push hips forward to stretch hip flexor."},
                    ],
                },
                {
                    "id": "hamstring-stretch",
                    "name": "Hamstring Stretch",
                    "type": "cooldown",
                    "repRange": "60s",
                    "notes": "",
                    "defaultSets": 1,
                    "wikiUrl": "",
                    "progressions": [
                        {"name": "Standing Forward Fold", "description": "Feet hip-width, hinge forward, let head hang. Grab elbows for deeper stretch."},
                    ],
                },
                {
                    "id": "pigeon-pose",
                    "name": "Pigeon Pose",
                    "type": "cooldown",
                    "repRange": "60s each",
                    "notes": "",
                    "defaultSets": 1,
                    "wikiUrl": "",
                    "progressions": [
                        {"name": "Pigeon Pose", "description": "From plank, bring one knee forward behind wrist. Extend back leg. Lower to forearms for deeper stretch."},
                    ],
                },
            ],
        },
    ],
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_id(raw: str) -> str:
    """Slugify an ID so it's safe as a filename."""
    s = raw.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s[:60] or str(uuid.uuid4())[:8]


def _routines_dir():
    return resolve_sandboxed_path(ROUTINES_DIR)


def _routine_path(routine_id: str):
    return resolve_sandboxed_path(f"{ROUTINES_DIR}/{_safe_id(routine_id)}.json")


def _seed_if_empty():
    """Write the BWF RR seed file if the routines dir has no JSON files yet."""
    rdir = _routines_dir()
    rdir.mkdir(parents=True, exist_ok=True)
    if not any(rdir.glob("*.json")):
        seed_path = rdir / "bwf-rr.json"
        seed_path.write_text(json.dumps(_BWF_RR, indent=2))


def _log_path(date_str: str):
    return resolve_sandboxed_path(f"{LOGS_DIR}/{date_str}.json")


def _today() -> _date:
    return _date.today()


# ── Routine endpoints ─────────────────────────────────────────────────────────

@router.get("/routines")
async def list_routines():
    """List all routines, seeding defaults on first call."""
    try:
        _seed_if_empty()
        rdir = _routines_dir()
    except SandboxError as e:
        raise HTTPException(status_code=403, detail=str(e))

    routines = []
    for f in sorted(rdir.glob("*.json")):
        try:
            routines.append(json.loads(f.read_text()))
        except json.JSONDecodeError:
            pass
    return routines


@router.get("/routines/{routine_id}")
async def get_routine(routine_id: str):
    try:
        path = _routine_path(routine_id)
    except SandboxError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if not path.exists():
        raise HTTPException(status_code=404, detail="Routine not found")

    return json.loads(path.read_text())


@router.post("/routines")
async def create_routine(routine: Routine):
    """Create a new routine. Generates an ID if not provided."""
    if not routine.id:
        routine = routine.model_copy(update={"id": str(uuid.uuid4())[:8]})

    try:
        path = _routine_path(routine.id)
    except SandboxError as e:
        raise HTTPException(status_code=403, detail=str(e))

    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        raise HTTPException(status_code=409, detail=f"Routine '{routine.id}' already exists")

    path.write_text(routine.model_dump_json(indent=2))
    return routine


@router.put("/routines/{routine_id}")
async def update_routine(routine_id: str, routine: Routine):
    """Update (overwrite) a routine."""
    try:
        path = _routine_path(routine_id)
    except SandboxError as e:
        raise HTTPException(status_code=403, detail=str(e))

    path.parent.mkdir(parents=True, exist_ok=True)
    # Ensure stored ID matches URL
    data = routine.model_copy(update={"id": routine_id})
    path.write_text(data.model_dump_json(indent=2))
    return data


@router.delete("/routines/{routine_id}")
async def delete_routine(routine_id: str):
    try:
        path = _routine_path(routine_id)
    except SandboxError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if not path.exists():
        raise HTTPException(status_code=404, detail="Routine not found")

    path.unlink()
    return {"status": "deleted", "id": routine_id}


# ── Log endpoints ─────────────────────────────────────────────────────────────

@router.get("/logs")
async def get_workout_log(date: str | None = None):
    date_str = date or str(_today())
    try:
        path = _log_path(date_str)
    except SandboxError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if not path.exists():
        return {"date": date_str, "log": None}

    try:
        return {"date": date_str, "log": json.loads(path.read_text())}
    except json.JSONDecodeError:
        return {"date": date_str, "log": None}


@router.post("/logs")
async def save_workout_log(log: WorkoutLog):
    date_str = log.date or str(_today())
    try:
        path = _log_path(date_str)
    except SandboxError as e:
        raise HTTPException(status_code=403, detail=str(e))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(log.model_dump_json(indent=2))
    return {"status": "saved", "date": date_str}


@router.get("/recent")
async def get_recent_workouts():
    today = _today()
    dates: list[str] = []

    try:
        base = resolve_sandboxed_path(LOGS_DIR)
    except SandboxError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if not base.exists():
        return {"dates": []}

    for i in range(30):
        d = today - timedelta(days=i)
        if (base / f"{d}.json").exists():
            dates.append(str(d))

    return {"dates": dates}
