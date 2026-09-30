from langsmith import traceable
from travel_planner.transport.state import (
    TransportState,
    RailTransportResult,
    TrainConnectivityResult,
)
from travel_planner.transport.tools.rail.station_tool import find_nearby_railway_stations
from travel_planner.transport.rail_graph import create_rail_graph, RailState


@traceable(run_type="chain", name="check_rail_stations")
def check_rail_stations(state: TransportState) -> dict:
    """
    Step 5/8A physical station discovery node:
    Discovers physical railway stations near source and destination without
    evaluating train connectivity.
    """
    source = state["source"]
    destination = state["destination"]
    spatial_result = find_nearby_railway_stations(source=source, destination=destination)

    return {
        "rail_result": RailTransportResult(
            station_discovery=spatial_result,
            train_connectivity=TrainConnectivityResult(
                status="NOT_CHECKED",
                error_message="Train connectivity not evaluated in station-only check",
            ),
        ),
    }


@traceable(run_type="chain", name="check_rail_connectivity")
def check_rail_connectivity(state: TransportState) -> dict:
    """
    Step 8B full multi-stage rail connectivity node:
    Invokes the internal Rail Subgraph:
    START -> station_discovery -> station_code_resolution -> train_connectivity -> finalize_rail -> END
    and puts the resulting RailTransportResult into state['rail_result'].
    """
    source = state["source"]
    destination = state["destination"]
    date_of_travel = state.get("date_of_travel")

    rail_graph = create_rail_graph()
    rail_input: RailState = {
        "source": source,
        "destination": destination,
        "date_of_travel": date_of_travel,
        "station_discovery": None,
        "source_station_codes": [],
        "destination_station_codes": [],
        "train_connectivity": None,
        "train_enrichment": None,
        "result": None,
    }

    rail_output = rail_graph.invoke(rail_input)
    rail_result = rail_output.get("result")

    return {
        "rail_result": rail_result,
    }
