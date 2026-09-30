import os
import sys

# Ensure src/ is on python path
sys.path.insert(0, os.path.abspath("src"))

# Handle Windows cp1252 printing Hawaiian Okina or other unicode characters
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

import uuid
from travel_planner.travel.travelgraph import create_travel_graph
from travel_planner.transport.state import (
    RailTransportResult,
    RailStationDiscoveryResult,
    TrainConnectivityResult,
)


def run_tests():
    app = create_travel_graph()

    print("=" * 70)
    print("TEST 1: Valid Road Route & Rail Services (Hyderabad -> Bengaluru)")
    print("=" * 70)

    config_1 = {"configurable": {"thread_id": str(uuid.uuid4())}}
    initial_input_1 = {
        "prompt": "Plan a 5-day trip from Hyderabad to Bengaluru on October 15 with a budget of 30000",
        "destination": [],
        "source": None,
        "date_of_travel": None,
        "number_of_days": None,
        "budget": None,
        "transportation": None,
    }

    final_state_1 = app.invoke(initial_input_1, config=config_1)

    print("\n--- Final TravelState (Test 1) ---")
    print(f"Destination:    {final_state_1.get('destination')}")
    print(f"Source:         {final_state_1.get('source')}")
    print(f"Date:           {final_state_1.get('date_of_travel')}")
    print(f"Days:           {final_state_1.get('number_of_days')}")
    print(f"Budget:         {final_state_1.get('budget')}")
    
    transportation = final_state_1.get("transportation")
    print(f"Transportation Domain Result: {transportation}")
    
    assert transportation is not None, "Transportation domain result should be populated in parent state!"
    road_result = transportation.road
    rail_result = transportation.rail

    assert road_result is not None, "Road route result should be populated under transportation.road!"
    assert rail_result is not None, "Rail result should be populated under transportation.rail!"
    assert isinstance(rail_result, RailTransportResult), "transportation.rail must be RailTransportResult"
    assert isinstance(rail_result.station_discovery, RailStationDiscoveryResult), "station_discovery must be RailStationDiscoveryResult"
    assert isinstance(rail_result.train_connectivity, TrainConnectivityResult), "train_connectivity must be TrainConnectivityResult"

    print(f"\n[ROAD] Available: {road_result.available} | Status: {road_result.status} | Distance: {road_result.distance_km} km | Duration: {road_result.duration_formatted}")
    print(f"[RAIL - STATIONS] Status: {rail_result.station_discovery.status} | Source Stations: {len(rail_result.source_stations)} | Destination Stations: {len(rail_result.destination_stations)}")
    print(f"[RAIL - TRAINS]   Status: {rail_result.train_connectivity.status} | Discovered: {len(rail_result.trains)}")
    if rail_result.train_enrichment:
        print(f"[RAIL - ENRICH]   Status: {rail_result.train_enrichment.status} | Enriched entries: {len(rail_result.train_enrichment.trains)}")
    assert hasattr(rail_result, "train_enrichment")
    assert transportation.train_enrichment == rail_result.train_enrichment

    assert road_result.available is True
    assert road_result.status == "ROUTE_FOUND"
    assert rail_result.station_discovery.status == "STATIONS_FOUND"
    assert len(rail_result.source_stations) > 0
    assert len(rail_result.destination_stations) > 0
    assert rail_result.train_connectivity.status in ("TRAINS_FOUND", "API_ERROR")

    # Assert Transportation Decision Agent output in TravelState
    recommendation = final_state_1.get("transportation_recommendation")
    print(f"\n[DECISION AGENT RECOMMENDATION] Status: {getattr(recommendation, 'status', None)} | Recommended Option: {getattr(recommendation, 'recommended_option', None)}")
    print(f"Reasoning: {getattr(recommendation, 'primary_recommendation_reason', None)}")
    print(f"Limitations: {getattr(recommendation, 'limitations', None)}")
    assert recommendation is not None, "transportation_recommendation must be populated in TravelState!"
    assert recommendation.status in ("RECOMMENDATION_MADE", "DECISION_ERROR", "NO_VIABLE_OPTION")

    print("\n[PASS] SUCCESS: Test 1 passed (Road and Multi-Stage Rail unified in TransportationResult, and Decision Agent recommendation generated).\n")

    print("=" * 70)
    print("TEST 2: Independent Failure Preserved (Mumbai -> Honolulu)")
    print("=" * 70)

    config_2 = {"configurable": {"thread_id": str(uuid.uuid4())}}
    initial_input_2 = {
        "prompt": "Plan a 4-day trip from Mumbai to Honolulu on Nov 1 with a budget of 50000",
        "destination": [],
        "source": None,
        "date_of_travel": None,
        "number_of_days": None,
        "budget": None,
        "transportation": None,
        "transportation_recommendation": None,
    }

    final_state_2 = app.invoke(initial_input_2, config=config_2)

    print("\n--- Final TravelState (Test 2) ---")
    print(f"Destination:    {final_state_2.get('destination')}")
    print(f"Source:         {final_state_2.get('source')}")
    
    transportation_2 = final_state_2.get("transportation")
    print(f"Transportation Domain Result: {transportation_2}")
    assert transportation_2 is not None, "Transportation domain result should be populated!"
    
    road_result_2 = transportation_2.road
    rail_result_2 = transportation_2.rail
    assert road_result_2 is not None, "Road route result should be populated even on routing failure!"
    assert rail_result_2 is not None, "Rail result should be populated even when destination has no stations!"

    print(f"\n[ROAD] Available: {road_result_2.available} | Status: {road_result_2.status} | Error: {road_result_2.error_message}")
    print(f"[RAIL] Station Status: {rail_result_2.station_discovery.status} | Train Status: {rail_result_2.train_connectivity.status}")

    assert road_result_2.available is False
    assert road_result_2.status == "NO_ROUTE_EXISTS"
    assert rail_result_2.station_discovery.status == "NO_DESTINATION_STATION"
    assert rail_result_2.train_connectivity.status == "NOT_CHECKED"

    recommendation_2 = final_state_2.get("transportation_recommendation")
    print(f"\n[DECISION AGENT RECOMMENDATION] Status: {getattr(recommendation_2, 'status', None)} | Recommended Option: {getattr(recommendation_2, 'recommended_option', None)}")
    print(f"Reasoning: {getattr(recommendation_2, 'primary_recommendation_reason', None)}")
    assert recommendation_2 is not None, "transportation_recommendation must be populated even when no viable option exists!"
    assert recommendation_2.status == "NO_VIABLE_OPTION"
    assert recommendation_2.recommended_option == "none"

    print("\n[PASS] SUCCESS: Test 2 passed (Road NO_ROUTE_EXISTS, Rail NO_DESTINATION_STATION, and Decision Agent NO_VIABLE_OPTION cleanly preserved).\n")


if __name__ == "__main__":
    run_tests()
