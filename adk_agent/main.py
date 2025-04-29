from google.adk import Agent 

from adk_agent.tools.goal_planner_tools import break_goal_into_tasks
from adk_agent.tools.calendar_tools import schedule_task_in_calendar

def create_agent():
    tools = [break_goal_into_tasks,
            schedule_task_in_calendar]
    
    agent = Agent(
        tools=tools,
        model="gemini-2.0-flash",
    )
    return agent

if __name__ == "__main__":
    agent = create_agent()
    agent.run(host="0.0.0.0", port=8080)
