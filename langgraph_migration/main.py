import asyncio
from typing import Annotated

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages 
from langchain_core.messages import HumanMessage,SystemMessage,AIMessage
from state import AgentState, ScheduleState, RequestedTasks

from pathlib import Path


model ="qwen2.5:3b"
SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts/system_prompt.md"
with open(SYSTEM_PROMPT_PATH, "r") as f:
    SCHEDULER_MODEL_SYSTEM_PROMPT = f.read()
TASKS_prompt =  " Break down below the user input into multiple individual tasks"


from langchain_ollama import ChatOllama
llm = ChatOllama(model=model, temperature=1.5, verbose=True )



# --- Nodes ---

def receive_user_input(state: AgentState) -> AgentState:
    # Simulate receiving user message
    print("\n>>> Waiting for user input...")
    user_input = input("User: ").strip()
    if user_input.lower() == "exit":
        raise KeyboardInterrupt
    if user_input.lower() == "print": 
        print("\n===== STATE SNAPSHOT =====")
        # Pretty‑print the full state
        print(state.model_dump_json(indent=2))
        print("===== END SNAPSHOT =====\n")
        return state
    new_msg = HumanMessage(content=user_input)
    state.messages.append(new_msg)
    state.request = user_input
    return state

def breakdown_tasks(state:AgentState) -> AgentState:
    system_msg = SystemMessage(
    content=TASKS_prompt + "\n\nUser: " + state.messages[-1].content
)
    print("\n=========Breakdown Tasks=============")
    print(state.messages[-1])
    # llm = ChatOllama(model=model, temperature=1.5, verbose=True )
    task_llm =llm.with_structured_output(RequestedTasks)
    response: RequestedTasks = task_llm.invoke([system_msg])
    state.tasks = response
    return state
def call_llm(state: AgentState) -> AgentState:
    # Compose LLM input from past messages
    response = llm.invoke(state.messages)
    print("AI:", response.content)

    state.messages.append(response)
    return state


# --- Build Graph ---

builder = StateGraph(AgentState)
builder.add_node("receive", receive_user_input)
# builder.add_node("breakdownTasks", breakdown_tasks)
builder.add_node("respond", call_llm)

builder.set_entry_point("receive")
builder.add_edge("receive", "respond")
# builder.add_edge("respond", "breakdownTasks")
# builder.add_edge("breakdownTasks", "respond")

builder.add_edge("respond", "receive")  # Loop back for conversation
# builder.add_edge("respond", END)  # If you want one-turn interaction

graph = builder.compile()

# --- Run Loop ---

system_msg = SystemMessage(
    content=SCHEDULER_MODEL_SYSTEM_PROMPT
)
state = AgentState(messages=[system_msg])


try:
    asyncio.run(graph.ainvoke(state))
except KeyboardInterrupt:
    print("\nConversation ended.")