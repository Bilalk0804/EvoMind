from typing import Any, Dict, List
from datetime import datetime, timedelta


def _parse_date(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except Exception:
        # naive fallback: today + n days if integer
        try:
            n = int(s)
            return datetime.now() + timedelta(days=n)
        except Exception:
            return datetime.now()


def plan_tasks_tool(goal: str, deadline: str | None = None, max_steps: int = 8) -> Dict[str, Any]:
    """Plan concrete steps for a goal with rough durations and ordering.

    Args:
        goal: The user's objective.
        deadline: ISO datetime or days-from-now integer.
        max_steps: Upper bound on number of tasks.
    Returns:
        dict with ordered tasks and suggested timeline.
    """
    end = _parse_date(deadline) if deadline else datetime.now() + timedelta(days=2)
    start = datetime.now()
    total_hours = max(2, int((end - start).total_seconds() // 3600))
    per_task = max(1, total_hours // max(1, max_steps))

    tasks: List[Dict[str, Any]] = []
    for i in range(1, max_steps + 1):
        tasks.append({
            "id": f"task-{i}",
            "title": f"Step {i} for: {goal}",
            "estimate_hours": per_task,
            "depends_on": [f"task-{i-1}"] if i > 1 else [],
        })

    return {
        "goal": goal,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "total_hours": total_hours,
        "tasks": tasks,
    }


def get_schedule_tool(date: str | None = None) -> Dict[str, Any]:
    """Return a simple schedule skeleton for a given day (ISO date)."""
    d = _parse_date(date).date() if date else datetime.now().date()
    base = datetime.combine(d, datetime.min.time())
    slots = []
    for i, hour in enumerate([9, 11, 14, 16]):
        slots.append({
            "slot": i + 1,
            "start": (base.replace(hour=hour)).isoformat(),
            "end": (base.replace(hour=hour + 1)).isoformat(),
            "title": "Available",
        })
    return {"date": d.isoformat(), "slots": slots}


def add_event_tool(title: str, start: str, end: str, description: str | None = None) -> Dict[str, Any]:
    """Create an event structure (client can persist it in calendar)."""
    s = _parse_date(start)
    e = _parse_date(end)
    if e <= s:
        e = s + timedelta(hours=1)
    return {
        "title": title,
        "start": s.isoformat(),
        "end": e.isoformat(),
        "description": description or "",
        "status": "created",
    }


