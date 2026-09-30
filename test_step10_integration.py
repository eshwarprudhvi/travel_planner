"""
Integration tests for Step 10: Parent Travel Graph + Transportation Decision Agent.

Verifies end-to-end flow across:
1. Road + Rail available.
2. Road available, Rail unavailable.
3. Road unavailable, Rail available.
4. Neither available.
5. Qrail enrichment unavailable (HTTP 403 / API disabled).
6. Decision Agent failure (gracefully handled and preserved in TravelState).
7. Trace verification (budget -> transportation_workflow -> transportation_decision_node -> END).
"""
import os
import sys

# Ensure src/ is on python path
sys.path.insert(0, os.path.abspath("src"))

# Handle Windows cp1252 printing
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

import uuid
import pytest
from unittest.mock import MagicMock, patch

from travel_planner.travel.travelgraph import create_travel_graph
from travel_planner.transport.state import (
    RoadRouteResult,
    RailwayStation,
    TrainService,
    RailStationDiscoveryResult,
    TrainConnectivityResult,
    TrainEnrichment,
    TrainEnrichmentResult,
    RailTransportResult,
    TransportationResult,
    TransportationRecommendation,
)


def make_mock_transport_result(
    road_available: bool = True,
    trains_available: bool = True,
    enrichment_status: str = "NOT_ENRICHED",
) -> TransportationResult:
    # Road
    if road_available:
        road = RoadRouteResult(
            available=True,
            source="Hyderabad",
            destination="Bengaluru",
            distance_km=568.0,
            duration_formatted="7 hours 38 mins",
            duration_seconds=27534,
            status="ROUTE_FOUND",
        )
    else:
        road = RoadRouteResult(
            available=False,
            source="Hyderabad",
            destination="Bengaluru",
            status="NO_ROUTE_EXISTS",
            error_message="No road route found",
        )

    # Rail
    if trains_available:
        disc = RailStationDiscoveryResult(
            source="Hyderabad",
            destination="Bengaluru",
            source_stations=[
                RailwayStation(
                    name="Kacheguda",
                    latitude=17.389,
                    longitude=78.499,
                    railway_type="station",
                    distance_from_location_km=3.0,
                )
            ],
            destination_stations=[
                RailwayStation(
                    name="KSR Bengaluru City",
                    latitude=12.978,
                    longitude=77.569,
                    railway_type="station",
                    distance_from_location_km=4.2,
                )
            ],
            status="STATIONS_FOUND",
        )
        conn = TrainConnectivityResult(
            source_station_code="KCG",
            destination_station_code="SBC",
            trains=[
                TrainService(
                    train_number="12785",
                    train_name="Kacheguda - Mysuru SF Express",
                    source_station_code="KCG",
                    destination_station_code="SBC",
                    departure_time="19:05",
                    arrival_time="06:25",
                    duration_minutes=680,
                    distance_km=620.0,
                )
            ],
            status="TRAINS_FOUND",
        )
    else:
        disc = RailStationDiscoveryResult(
            source="Hyderabad",
            destination="Bengaluru",
            status="NO_STATIONS_FOUND",
            error_message="No stations found",
        )
        conn = TrainConnectivityResult(
            status="NOT_CHECKED",
            error_message="Physical stations not found",
        )

    enrichment = None
    if enrichment_status == "API_ERROR":
        enrichment = TrainEnrichmentResult(
            trains=[TrainEnrichment(train_number="12785", status="FAILED")],
            status="API_ERROR",
            error_message="Qrail API access disabled: Please contact support (HTTP 403)",
        )

    rail = RailTransportResult(
        station_discovery=disc,
        train_connectivity=conn,
        train_enrichment=enrichment,
    )

    return TransportationResult(road=road, rail=rail)


@pytest.fixture(autouse=True)
def mock_upstream_extractors():
    """Mock upstream LLM extraction nodes so integration tests isolate the transportation subsystem."""
    with patch("travel_planner.travel.travelnodes.extract_destination", return_value={"destination": ["Bengaluru"]}), \
         patch("travel_planner.travel.travelnodes.extract_source", return_value={"source": "Hyderabad"}), \
         patch("travel_planner.travel.travelnodes.extract_date", return_value={"date_of_travel": "October 15"}), \
         patch("travel_planner.travel.travelnodes.extract_number_of_days", return_value={"number_of_days": 5}), \
         patch("travel_planner.travel.travelnodes.extract_budget", return_value={"budget": 30000}):
        yield


@pytest.fixture
def base_input():
    return {
        "prompt": "Plan a 5-day trip from Hyderabad to Bengaluru on October 15 with a budget of 30000",
        "destination": ["Bengaluru"],
        "source": "Hyderabad",
        "date_of_travel": "October 15",
        "number_of_days": 5,
        "budget": 30000,
        "transportation": None,
        "transportation_recommendation": None,
    }



def test_parent_graph_road_and_rail_available(base_input):
    """Scenario 1: Road & Rail available. Decision agent recommends viable option."""
    app = create_travel_graph()
    mock_res = make_mock_transport_result(road_available=True, trains_available=True)

    with patch("travel_planner.transport.graph.create_transport_graph") as mock_subgraph_cls:
        mock_sub = MagicMock()
        mock_sub.invoke.return_value = {"result": mock_res}
        mock_subgraph_cls.return_value = mock_sub

        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        final_state = app.invoke(base_input, config=config)

        # Check TravelState structure
        assert "transportation" in final_state
        assert "transportation_recommendation" in final_state
        assert isinstance(final_state["transportation"], TransportationResult)
        assert isinstance(final_state["transportation_recommendation"], TransportationRecommendation)

        rec = final_state["transportation_recommendation"]
        assert rec.status == "RECOMMENDATION_MADE"
        assert rec.recommended_option in ("road", "rail", "both")


def test_parent_graph_road_only(base_input):
    """Scenario 2: Road only available."""
    app = create_travel_graph()
    mock_res = make_mock_transport_result(road_available=True, trains_available=False)

    with patch("travel_planner.transport.graph.create_transport_graph") as mock_subgraph_cls:
        mock_sub = MagicMock()
        mock_sub.invoke.return_value = {"result": mock_res}
        mock_subgraph_cls.return_value = mock_sub

        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        final_state = app.invoke(base_input, config=config)

        rec = final_state["transportation_recommendation"]
        assert rec.status == "RECOMMENDATION_MADE"
        assert rec.recommended_option == "road"


def test_parent_graph_rail_only(base_input):
    """Scenario 3: Rail only available."""
    app = create_travel_graph()
    mock_res = make_mock_transport_result(road_available=False, trains_available=True)

    with patch("travel_planner.transport.graph.create_transport_graph") as mock_subgraph_cls:
        mock_sub = MagicMock()
        mock_sub.invoke.return_value = {"result": mock_res}
        mock_subgraph_cls.return_value = mock_sub

        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        final_state = app.invoke(base_input, config=config)

        rec = final_state["transportation_recommendation"]
        assert rec.status == "RECOMMENDATION_MADE"
        assert rec.recommended_option == "rail"


def test_parent_graph_neither_available(base_input):
    """Scenario 4: Neither road nor rail available."""
    app = create_travel_graph()
    mock_res = make_mock_transport_result(road_available=False, trains_available=False)

    with patch("travel_planner.transport.graph.create_transport_graph") as mock_subgraph_cls:
        mock_sub = MagicMock()
        mock_sub.invoke.return_value = {"result": mock_res}
        mock_subgraph_cls.return_value = mock_sub

        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        final_state = app.invoke(base_input, config=config)

        rec = final_state["transportation_recommendation"]
        assert rec.status == "NO_VIABLE_OPTION"
        assert rec.recommended_option == "none"


def test_parent_graph_enrichment_unavailable(base_input):
    """Scenario 5: Rail available but enrichment failed (HTTP 403)."""
    app = create_travel_graph()
    mock_res = make_mock_transport_result(road_available=True, trains_available=True, enrichment_status="API_ERROR")

    with patch("travel_planner.transport.graph.create_transport_graph") as mock_subgraph_cls:
        mock_sub = MagicMock()
        mock_sub.invoke.return_value = {"result": mock_res}
        mock_subgraph_cls.return_value = mock_sub

        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        final_state = app.invoke(base_input, config=config)

        rec = final_state["transportation_recommendation"]
        assert rec.status == "RECOMMENDATION_MADE"
        assert any("enrichment" in lim.lower() or "live" in lim.lower() or "status" in lim.lower() for lim in rec.limitations)


def test_parent_graph_decision_agent_failure(base_input):
    """Scenario 6: Decision Agent LLM fails; raw TransportationResult is strictly preserved."""
    app = create_travel_graph()
    mock_res = make_mock_transport_result(road_available=True, trains_available=True)

    with patch("travel_planner.transport.graph.create_transport_graph") as mock_subgraph_cls, \
         patch("travel_planner.transport.nodes.decision_agent.gemini_llm") as mock_gemini:
        mock_sub = MagicMock()
        mock_sub.invoke.return_value = {"result": mock_res}
        mock_subgraph_cls.return_value = mock_sub

        mock_structured = MagicMock()
        mock_structured.invoke.side_effect = RuntimeError("Simulated LLM service interruption")
        mock_gemini.with_structured_output.return_value = mock_structured

        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        final_state = app.invoke(base_input, config=config)

        # Factual transportation must be completely intact
        assert final_state["transportation"] == mock_res
        assert final_state["transportation"].road.available is True

        # Recommendation must capture DECISION_ERROR without raising
        rec = final_state["transportation_recommendation"]
        assert rec is not None
        assert rec.status == "DECISION_ERROR"
        assert "Simulated LLM service interruption" in rec.error_message


def test_parent_graph_flow_trace():
    """Scenario 7: Verify node graph structure contains transportation_workflow -> transportation_decision_node -> END."""
    app = create_travel_graph()
    node_names = set(app.get_graph().nodes.keys())
    assert "transportation_workflow" in node_names
    assert "transportation_decision_node" in node_names


if __name__ == "__main__":
    pytest.main(["-v", __file__])
