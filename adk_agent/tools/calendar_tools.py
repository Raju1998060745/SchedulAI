
from datetime import datetime, timedelta

def schedule_task_in_calendar(task: str, preferred_start_time: str = None) -> dict:
    """
    Pretends to schedule a task on a calendar.
    If no preferred time is given, schedules for now + 1 hour.
    """

    if preferred_start_time:
        start_time = datetime.fromisoformat(preferred_start_time)
    else:
        start_time = datetime.utcnow() + timedelta(hours=1)

    end_time = start_time + timedelta(hours=1)

    # Dummy response - later we'll call real Google Calendar API here
    return {
        "task": task,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "status": "Scheduled (dummy)"
    }
