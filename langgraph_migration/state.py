from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph


class ScheduleState(TypedDict):
    raw_input: str
    parsed_intent: Dict[str, Any]  # {"date": ..., "time": ..., "participants": ..., etc.}
    conflicts: Optional[List[str]]
    confirmed: bool
    event_created: bool

class RequestedTasks(BaseModel):
    """
    Break down of user requested tasks into user intent into tasks
    """
    tasks: List[str] = Field(
        default_factory=list, description="A list of tasks to be scheduled."
    )



class AgentState(BaseModel):
    """
    Represents the state of our scheduling agent.
    Using Pydantic BaseModel as the core state object.
    """
    request: Optional[str] = Field(
        None, description="The initial goal or request from the user."
    )
    tasks: Optional[RequestedTasks]= None

    schedule: Optional[str] = Field(
        None, description="The user's current calendar schedule as a string."
    )
    messages: List[BaseMessage] = Field(
        default_factory=list, description="The history of the conversation."
    )

    class Config:
        # Pydantic config to allow arbitrary types like BaseMessage
        arbitrary_types_allowed = True
