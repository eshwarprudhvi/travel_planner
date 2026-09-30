"""
Rail Subgraph Implementation.
Executes the multi-stage Rail transportation pipeline:
START
  ↓
station_discovery (OpenStreetMap/Overpass spatial query)
  ↓
station_code_resolution (OSM names -> Indian Railways codes)
  ↓
train_connectivity (RailRadar scheduled train discovery)
  ↓
train_enrichment (Qrail details & live running status per train)
  ↓
finalize_rail (Packages into unified RailTransportResult)
  ↓
END
"""
from typing import Optional, TypedDict
from langsmith import traceable
from langgraph.graph import StateGraph, START, END

from travel_planner.transport.state import (
    RailStationDiscoveryResult,
    TrainConnectivityResult,
    TrainEnrichmentResult,
    RailTransportResult,
)
from travel_planner.transport.tools.rail.station_tool import find_nearby_railway_stations
from travel_planner.transport.tools.rail.trains_tool import discover_train_services
from travel_planner.transport.tools.rail.enrichment_tool import enrich_discovered_trains
from travel_planner.transport.services.station_code_resolver import resolve_station_code


class RailState(TypedDict):
    source: str
    destination: str
    date_of_travel: Optional[str]
    station_discovery: Optional[RailStationDiscoveryResult]
    source_station_codes: list[str]
    destination_station_codes: list[str]
    train_connectivity: Optional[TrainConnectivityResult]
    train_enrichment: Optional[TrainEnrichmentResult]
    result: Optional[RailTransportResult]


@traceable(run_type="chain", name="rail_station_discovery_node")
def station_discovery_node(state: RailState) -> dict:
    """
    Stage 1: Discovers physical passenger railway stations near source and destination.
    """
    source = state["source"]
    destination = state["destination"]
    discovery_result = find_nearby_railway_stations(source=source, destination=destination)

    return {
        "station_discovery": discovery_result,
    }


def route_after_station_discovery(state: RailState) -> str:
    """
    Routes to station_code_resolution only if physical stations were found at both endpoints.
    Otherwise skips directly to finalize_rail.
    """
    disc = state.get("station_discovery")
    if disc and disc.status == "STATIONS_FOUND":
        return "station_code_resolution"
    return "finalize_rail"


@traceable(run_type="chain", name="rail_station_code_resolution_node")
def station_code_resolution_node(state: RailState) -> dict:
    """
    Stage 2: Resolves physical OSM railway station names to official IR station codes.
    """
    disc = state["station_discovery"]
    if not disc:
        return {"source_station_codes": [], "destination_station_codes": []}

    source_codes = []
    for st in disc.source_stations:
        code = resolve_station_code(st.name)
        if code and code not in source_codes:
            source_codes.append(code)
            if len(source_codes) >= 3:
                break

    dest_codes = []
    for st in disc.destination_stations:
        code = resolve_station_code(st.name)
        if code and code not in dest_codes:
            dest_codes.append(code)
            if len(dest_codes) >= 3:
                break

    return {
        "source_station_codes": source_codes,
        "destination_station_codes": dest_codes,
    }


@traceable(run_type="chain", name="rail_train_connectivity_node")
def train_connectivity_node(state: RailState) -> dict:
    """
    Stage 3: Discovers scheduled train services between candidate station code pairs.
    """
    source_codes = state.get("source_station_codes", [])
    dest_codes = state.get("destination_station_codes", [])
    date_of_travel = state.get("date_of_travel")

    connectivity_result = discover_train_services(
        source_codes=source_codes,
        dest_codes=dest_codes,
        date_of_travel=date_of_travel,
        max_source_stations=3,
        max_destination_stations=3,
    )

    return {
        "train_connectivity": connectivity_result,
    }


def route_after_train_connectivity(state: RailState) -> str:
    """
    Routes to train_enrichment only if scheduled trains were found.
    Otherwise skips directly to finalize_rail.
    """
    conn = state.get("train_connectivity")
    if conn and conn.status == "TRAINS_FOUND" and conn.trains:
        return "train_enrichment"
    return "finalize_rail"


@traceable(run_type="chain", name="rail_train_enrichment_node")
def train_enrichment_node(state: RailState) -> dict:
    """
    Stage 4: Enriches discovered trains with details and running status via Qrail.
    """
    conn = state.get("train_connectivity")
    if not conn or not conn.trains:
        return {
            "train_enrichment": TrainEnrichmentResult(
                trains=[],
                status="NOT_ENRICHED",
                error_message="No train services available to enrich.",
            )
        }

    train_numbers = [t.train_number for t in conn.trains]
    enrichment_result = enrich_discovered_trains(train_numbers)

    return {
        "train_enrichment": enrichment_result,
    }


@traceable(run_type="chain", name="finalize_rail_node")
def finalize_rail_node(state: RailState) -> dict:
    """
    Stage 5: Packages station discovery, train connectivity, and enrichment into unified RailTransportResult.
    """
    disc = state.get("station_discovery")
    conn = state.get("train_connectivity")
    enrichment = state.get("train_enrichment")

    if not conn:
        status_msg = disc.status if disc else "UNKNOWN"
        conn = TrainConnectivityResult(
            status="NOT_CHECKED",
            error_message=f"Train connectivity not checked (station discovery status: {status_msg})",
        )

    rail_result = RailTransportResult(
        station_discovery=disc,
        train_connectivity=conn,
        train_enrichment=enrichment,
    )

    return {
        "result": rail_result,
    }


def create_rail_graph():
    """
    Builds and compiles the internal Rail Subgraph:
    START -> station_discovery -> station_code_resolution -> train_connectivity -> train_enrichment -> finalize_rail -> END
    """
    workflow = StateGraph(RailState)

    workflow.add_node("station_discovery", station_discovery_node)
    workflow.add_node("station_code_resolution", station_code_resolution_node)
    workflow.add_node("train_connectivity", train_connectivity_node)
    workflow.add_node("train_enrichment", train_enrichment_node)
    workflow.add_node("finalize_rail", finalize_rail_node)

    workflow.add_edge(START, "station_discovery")

    workflow.add_conditional_edges(
        "station_discovery",
        route_after_station_discovery,
        {
            "station_code_resolution": "station_code_resolution",
            "finalize_rail": "finalize_rail",
        },
    )

    workflow.add_edge("station_code_resolution", "train_connectivity")

    workflow.add_conditional_edges(
        "train_connectivity",
        route_after_train_connectivity,
        {
            "train_enrichment": "train_enrichment",
            "finalize_rail": "finalize_rail",
        },
    )

    workflow.add_edge("train_enrichment", "finalize_rail")
    workflow.add_edge("finalize_rail", END)

    return workflow.compile()

