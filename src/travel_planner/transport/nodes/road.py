from langsmith import traceable
from travel_planner.transport.state import TransportState, TransportationResult
from travel_planner.transport.tools.road.routes_tool import compute_road_route


@traceable(run_type="chain", name="check_road_route")
def check_road_route(state: TransportState) -> dict:
    """
    Transportation subgraph node (Road capability):
    Invokes the road routing tool with state['source'] and state['destination'],
    and updates state['road_result'].
    """
    source = state["source"]
    destination = state["destination"]
    road_result = compute_road_route(source=source, destination=destination)

    return {
        "road_result": road_result,
    }


