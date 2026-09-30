from langgraph.graph import StateGraph, START, END
from .state import TransportState
from .nodes.road import check_road_route
from .nodes.rail import check_rail_connectivity
from .nodes.aggregate import aggregate_transportation


def create_transport_graph():
    """
    Builds the transportation subgraph.
    Sequentially executes modal capabilities (Road, Rail) and aggregates
    the results into a unified domain-level TransportationResult.
    """
    workflow = StateGraph(TransportState)

    # Add modal nodes
    workflow.add_node("check_road_route", check_road_route)
    workflow.add_node("check_rail", check_rail_connectivity)
    workflow.add_node("aggregate_transportation", aggregate_transportation)

    # Modal pipeline flow: START -> Road -> Rail -> Aggregation -> END
    workflow.add_edge(START, "check_road_route")
    workflow.add_edge("check_road_route", "check_rail")
    workflow.add_edge("check_rail", "aggregate_transportation")
    workflow.add_edge("aggregate_transportation", END)

    return workflow.compile()

