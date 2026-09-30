"""
Transportation Subgraph Result Aggregation Node.
Combines modal results (Road, Rail) into the unified domain-level TransportationResult.
Does NOT perform any external API calls.
"""
from langsmith import traceable
from travel_planner.transport.state import TransportState, TransportationResult


@traceable(run_type="chain", name="aggregate_transportation")
def aggregate_transportation(state: TransportState) -> dict:
    """
    Collects road_result and rail_result from TransportState
    and packages them into a clean, unified TransportationResult.
    """
    return {
        "result": TransportationResult(
            road=state.get("road_result"),
            rail=state.get("rail_result"),
        )
    }
