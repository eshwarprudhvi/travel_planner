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
    extract_date,
    route_date,
    ask_date,
    extract_number_of_days,
    route_number_of_days,
    ask_number_of_days,
    extract_budget,
    route_budget,
    ask_budget,
    transportation_workflow,
    transportation_decision_node,
)


def create_travel_graph(checkpointer=None):
    """
    Builds and compiles the travel planning subgraph (destination, source, date, duration, budget, and transportation).
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

    # Date nodes
    workflow.add_node("extract_date", extract_date)
    workflow.add_node("ask_date", ask_date)

    # Number of days nodes
    workflow.add_node("extract_number_of_days", extract_number_of_days)
    workflow.add_node("ask_number_of_days", ask_number_of_days)

    # Budget nodes
    workflow.add_node("extract_budget", extract_budget)
    workflow.add_node("ask_budget", ask_budget)

    # Transportation nodes
    workflow.add_node("transportation_workflow", transportation_workflow)
    workflow.add_node("transportation_decision_node", transportation_decision_node)

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
            "continue": "extract_date",
        }
    )

    workflow.add_edge("ask_source", "extract_source")

    # Date flow
    workflow.add_conditional_edges(
        "extract_date",
        route_date,
        {
            "ask_date": "ask_date",
            "continue": "extract_number_of_days",
        }
    )

    workflow.add_edge("ask_date", "extract_date")

    # Number of days flow
    workflow.add_conditional_edges(
        "extract_number_of_days",
        route_number_of_days,
        {
            "ask_number_of_days": "ask_number_of_days",
            "continue": "extract_budget",
        }
    )

    workflow.add_edge("ask_number_of_days", "extract_number_of_days")

    # Budget flow
    workflow.add_conditional_edges(
        "extract_budget",
        route_budget,
        {
            "ask_budget": "ask_budget",
            "continue": "transportation_workflow",
        }
    )

    workflow.add_edge("ask_budget", "extract_budget")

    # Transportation flow
    workflow.add_edge("transportation_workflow", "transportation_decision_node")
    workflow.add_edge("transportation_decision_node", END)

    if checkpointer is None:
        checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)

