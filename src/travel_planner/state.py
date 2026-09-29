from typing import Literal
from pydantic import BaseModel
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages 

class AgentState(BaseModel):
    prompt : str
    intent : Literal["TRAVEL", "NOT_TRAVEL"]
    messages: list[AnyMessage, add_messages]
    non_travel_attempts: int = 0
    