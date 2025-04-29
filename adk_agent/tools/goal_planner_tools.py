def break_goal_into_tasks(goal: str) -> list:
    """Breaks a goal into a list of subtasks."""
    tasks = [
        f"Research about {goal}",
        f"Draft a plan for {goal}",
        f"Write initial draft of {goal}",
        f"Finalize and review {goal}"
    ]
    return tasks
