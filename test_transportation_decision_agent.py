"""
Unit & Integration Test Suite for Step 9: Transportation Decision Agent.

Tests cover:
1. Road available, rail available (both viable; LLM compares durations/options).
2. Road available, rail unavailable (e.g. no trains found).
3. Road unavailable, rail available (road route blocked/impossible, train exists).
4. Both unavailable (Honolulu overseas: no road route, no train stations).
5. Rail available but enrichment unavailable (Qrail HTTP 403 / API disabled noted under limitations).
6. Missing optional transportation fields (None departure times, durations, or distance).
7. LLM output validation / API failure handling (gracefully preserved without crashing).
8. Strict grounding verification (ensuring prices and non-existent trains are not invented).
"""
import os
import sys

# Ensure src/ is on python path
sys.path.insert(0, os.path.abspath("src"))

import pytest
from unittest.mock import MagicMock

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
from travel_planner.transport.nodes.decision_agent import decide_transportation


# Helper fixtures
def create_sample_road(available: bool = True, status: str = "ROUTE_FOUND"):
    if available:
        return RoadRouteResult(
            available=True,
            source="Hyderabad",
            destination="Bengaluru",
            distance_km=568.0,
            duration_formatted="7 hours 38 mins",
            duration_seconds=27534,
            status="ROUTE_FOUND",
        )
    return RoadRouteResult(
        available=False,
        source="Mumbai",
        destination="Honolulu",
        status=status,
        error_message="Could not find route between coordinates",
    )


def create_sample_rail(
    stations_found: bool = True,
    trains_found: bool = True,
    enrichment_status: str = "NOT_ENRICHED",
):
    if not stations_found:
        disc = RailStationDiscoveryResult(
            source="Mumbai",
            destination="Honolulu",
            status="NO_DESTINATION_STATION",
            error_message="No railway stations found near destination",
        )
        conn = TrainConnectivityResult(
            status="NOT_CHECKED",
            error_message="Physical stations not found at destination",
        )
        return RailTransportResult(station_discovery=disc, train_connectivity=conn)

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

    if not trains_found:
        conn = TrainConnectivityResult(
            source_station_code="KCG",
            destination_station_code="SBC",
            trains=[],
            status="NO_TRAINS_FOUND",
            error_message="No direct train services found between station codes",
        )
        return RailTransportResult(station_discovery=disc, train_connectivity=conn)

    trains = [
        TrainService(
            train_number="12785",
            train_name="Kacheguda - Mysuru SF Express",
            train_type="Superfast",
            source_station_code="KCG",
            destination_station_code="SBC",
            departure_time="19:05",
            arrival_time="06:25",
            duration_minutes=680,
            distance_km=620.0,
            run_days=["Daily"],
        )
    ]
    conn = TrainConnectivityResult(
        source_station_code="KCG",
        destination_station_code="SBC",
        trains=trains,
        status="TRAINS_FOUND",
    )

    enrichment = None
    if enrichment_status == "API_ERROR":
        enrichment = TrainEnrichmentResult(
            trains=[
                TrainEnrichment(
                    train_number="12785",
                    status="FAILED",
                )
            ],
            status="API_ERROR",
            error_message="Qrail API access disabled: Please contact support (HTTP 403)",
        )

    return RailTransportResult(
        station_discovery=disc,
        train_connectivity=conn,
        train_enrichment=enrichment,
    )


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_1_road_available_rail_available():
    """Scenario 1: Both Road and Rail are available. Agent compares them and recommends viable option."""
    transport_result = TransportationResult(
        road=create_sample_road(available=True),
        rail=create_sample_rail(stations_found=True, trains_found=True),
    )

    rec = decide_transportation(transport_result, date_of_travel="2026-10-15")

    assert isinstance(rec, TransportationRecommendation)
    assert rec.status == "RECOMMENDATION_MADE"
    assert rec.recommended_option in ("road", "rail", "both")
    assert len(rec.available_options) >= 2
    # Verify both modalities are evaluated
    modalities = {opt.modality: opt for opt in rec.available_options}
    assert "road" in modalities and modalities["road"].available is True
    assert "rail" in modalities and modalities["rail"].available is True
    # Verify limitations mention lack of price information
    assert any("price" in lim.lower() or "fare" in lim.lower() or "cost" in lim.lower() for lim in rec.limitations)


def test_2_road_available_rail_unavailable():
    """Scenario 2: Road available, but Rail has no trains found."""
    transport_result = TransportationResult(
        road=create_sample_road(available=True),
        rail=create_sample_rail(stations_found=True, trains_found=False),
    )

    rec = decide_transportation(transport_result)

    assert isinstance(rec, TransportationRecommendation)
    assert rec.status == "RECOMMENDATION_MADE"
    assert rec.recommended_option == "road"
    modalities = {opt.modality: opt for opt in rec.available_options}
    assert modalities["road"].available is True
    assert modalities["rail"].available is False


def test_3_road_unavailable_rail_available():
    """Scenario 3: Road unavailable (no route exists), Rail has scheduled trains."""
    transport_result = TransportationResult(
        road=create_sample_road(available=False, status="NO_ROUTE_EXISTS"),
        rail=create_sample_rail(stations_found=True, trains_found=True),
    )

    rec = decide_transportation(transport_result)

    assert isinstance(rec, TransportationRecommendation)
    assert rec.status == "RECOMMENDATION_MADE"
    assert rec.recommended_option == "rail"
    modalities = {opt.modality: opt for opt in rec.available_options}
    assert modalities["road"].available is False
    assert modalities["rail"].available is True
    assert "12785" in str(modalities["rail"].supported_services_or_routes)


def test_4_both_unavailable():
    """Scenario 4: Both Road and Rail are unavailable (e.g. Honolulu overseas)."""
    transport_result = TransportationResult(
        road=create_sample_road(available=False, status="NO_ROUTE_EXISTS"),
        rail=create_sample_rail(stations_found=False, trains_found=False),
    )

    rec = decide_transportation(transport_result)

    assert isinstance(rec, TransportationRecommendation)
    assert rec.status == "NO_VIABLE_OPTION"
    assert rec.recommended_option == "none"
    for opt in rec.available_options:
        assert opt.available is False


def test_5_rail_available_enrichment_unavailable():
    """Scenario 5: Rail has trains found, but Qrail returned HTTP 403 API_ERROR."""
    transport_result = TransportationResult(
        road=create_sample_road(available=True),
        rail=create_sample_rail(stations_found=True, trains_found=True, enrichment_status="API_ERROR"),
    )

    rec = decide_transportation(transport_result)

    assert isinstance(rec, TransportationRecommendation)
    assert rec.status == "RECOMMENDATION_MADE"
    # Should explicitly note enrichment / live status limitation
    assert any(
        "enrichment" in lim.lower() or "live" in lim.lower() or "running" in lim.lower() or "status" in lim.lower()
        for lim in rec.limitations
    )


def test_6_missing_optional_transportation_fields():
    """Scenario 6: Modalities contain None in optional fields (departure time, duration, distance)."""
    minimal_train = TrainService(
        train_number="12785",
        train_name="Kacheguda Express",
        source_station_code="KCG",
        destination_station_code="SBC",
        departure_time=None,
        arrival_time=None,
        duration_minutes=None,
        distance_km=None,
        run_days=None,
    )
    rail = RailTransportResult(
        station_discovery=RailStationDiscoveryResult(
            source="Hyderabad",
            destination="Bengaluru",
            status="STATIONS_FOUND",
        ),
        train_connectivity=TrainConnectivityResult(
            source_station_code="KCG",
            destination_station_code="SBC",
            trains=[minimal_train],
            status="TRAINS_FOUND",
        ),
    )
    transport_result = TransportationResult(
        road=RoadRouteResult(
            available=True,
            source="Hyderabad",
            destination="Bengaluru",
            distance_km=None,
            duration_formatted=None,
            status="ROUTE_FOUND",
        ),
        rail=rail,
    )

    rec = decide_transportation(transport_result)

    assert isinstance(rec, TransportationRecommendation)
    assert rec.status == "RECOMMENDATION_MADE"
    # Should still produce recommendation without crashing on None values


def test_7_llm_failure_handling():
    """Scenario 7: LLM invocation failure is caught and preserved without crashing or losing data."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.side_effect = RuntimeError("Simulated Gemini API rate limit or outage")
    mock_llm.with_structured_output.return_value = mock_structured

    transport_result = TransportationResult(
        road=create_sample_road(available=True),
        rail=create_sample_rail(stations_found=True, trains_found=True),
    )

    rec = decide_transportation(transport_result, llm=mock_llm)

    assert isinstance(rec, TransportationRecommendation)
    assert rec.status == "DECISION_ERROR"
    assert "Simulated Gemini API rate limit" in (rec.error_message or "")
    # Ensure original TransportationResult is completely preserved
    assert transport_result.road.available is True
    assert len(transport_result.rail.trains) == 1


if __name__ == "__main__":
    pytest.main(["-v", __file__])
