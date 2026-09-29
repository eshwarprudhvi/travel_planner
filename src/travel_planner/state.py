from typing import Annotated, Literal, Optional
from typing_extensions import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages 

class AgentState(TypedDict):
    prompt: str
    intent: Optional[Literal["TRAVEL", "NOT_TRAVEL"]]
    messages: Annotated[list[AnyMessage], add_messages]
    non_travel_attempts: int
    