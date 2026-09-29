from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from .travelState import TravelState
from .travelnodes import (
    extract_destination,
    route_destination,
    ask_destination,
    ask_choose_destination,
    validate_destination,
    extract_source,
    route_source,
    ask_source,
)


def create_travel_graph(checkpointer=None):
    """
    Builds and compiles the travel planning subgraph (destination & source collection).
    """
    workflow = StateGraph(TravelState)

    # Destination nodes
    workflow.add_node("extract_destination", extract_destination)
    workflow.add_node("ask_destination", ask_destination)
    workflow.add_node("ask_choose_destination", ask_choose_destination)
    workflow.add_node("validate_destination", validate_destination)

    # Source nodes
    workflow.add_node("extract_source", extract_source)
    workflow.add_node("ask_source", ask_source)

    # Destination flow
    workflow.add_edge(START, "extract_destination")

    workflow.add_conditional_edges(
        "extract_destination",
        route_destination,
        {
            "ask_destination": "ask_destination",
            "ask_choose_destination": "ask_choose_destination",
            "validate_destination": "validate_destination",
        }
    )

    workflow.add_edge("ask_destination", "extract_destination")
    workflow.add_edge("ask_choose_destination", "extract_destination")

    # Move from destination validation to source extraction
    workflow.add_edge("validate_destination", "extract_source")

    # Source flow
    workflow.add_conditional_edges(
        "extract_source",
        route_source,
        {
            "ask_source": "ask_source",
            "continue": END,  # Continues to next travel requirement (e.g. date) in future steps
        }
    )

    workflow.add_edge("ask_source", "extract_source")

    if checkpointer is None:
        checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)
