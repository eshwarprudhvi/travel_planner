from langgraph.graph import StateGraph, START, END
from .state import TransportState
from .nodes.road import check_road_route


def create_transport_graph():
    """
    Builds the transportation subgraph.
    Evaluates available travel modes (starting with Road) between source and destination.
    """
    workflow = StateGraph(TransportState)

    workflow.add_node("check_road_route", check_road_route)

    workflow.add_edge(START, "check_road_route")
    workflow.add_edge("check_road_route", END)

    return workflow.compile()
