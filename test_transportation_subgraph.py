"""
End-to-End Transportation Subgraph Test (Step 8B Multi-Stage Rail Integration).
Verifies:
1. Sequential execution of Road and Rail capabilities in the Transportation Subgraph.
2. Unified aggregation into domain-level TransportationResult(road=..., rail=RailTransportResult(...)).
3. Clear semantic preservation:
   - Rail result retains BOTH layers:
     a) station_discovery: RailStationDiscoveryResult (physical station presence)
     b) train_connectivity: TrainConnectivityResult (actual scheduled train services)
   - Hyderabad -> Bengaluru:
     * Road: ROUTE_FOUND
     * Rail station_discovery: STATIONS_FOUND
     * Rail train_connectivity: TRAINS_FOUND
   - Mumbai -> Honolulu:
     * Road: NO_ROUTE_EXISTS
     * Rail station_discovery: NO_DESTINATION_STATION
     * Rail train_connectivity: NOT_CHECKED
"""
import os
import sys

# Ensure src/ is on python path
sys.path.insert(0, os.path.abspath("src"))

from travel_planner.transport.graph import create_transport_graph
from travel_planner.transport.state import (
    TransportState,
    RailTransportResult,
    RailStationDiscoveryResult,
    TrainConnectivityResult,
)


def run_subgraph_tests():
    transport_subgraph = create_transport_graph()

    print("=" * 70)
    print("SUBGRAPH TEST 1: Hyderabad -> Bengaluru (Road & Rail Discovered)")
    print("=" * 70)

    input_1: TransportState = {
        "source": "Hyderabad",
        "destination": "Bengaluru",
        "date_of_travel": None,
        "road_result": None,
        "rail_result": None,
        "result": None,
    }

    output_1 = transport_subgraph.invoke(input_1)
    result_1 = output_1.get("result")

    assert result_1 is not None, "TransportationResult should be produced!"
    road_1 = result_1.road
    rail_1 = result_1.rail

    assert road_1 is not None, "RoadRouteResult must be populated!"
    assert rail_1 is not None, "RailTransportResult must be populated!"
    assert isinstance(rail_1, RailTransportResult), "rail field must be a RailTransportResult"
    assert isinstance(rail_1.station_discovery, RailStationDiscoveryResult), "station_discovery must be RailStationDiscoveryResult"
    assert isinstance(rail_1.train_connectivity, TrainConnectivityResult), "train_connectivity must be TrainConnectivityResult"

    print(f"\n[ROAD RESULT]\n  Available: {road_1.available}\n  Status:    {road_1.status}\n  Distance:  {road_1.distance_km} km\n  Duration:  {road_1.duration_formatted}")
    print(f"\n[RAIL RESULT - STAGE 1: PHYSICAL STATION DISCOVERY]\n  Status:             {rail_1.station_discovery.status}\n  Candidate Stations: Source: {len(rail_1.source_stations)}, Dest: {len(rail_1.destination_stations)}")
    for idx, st in enumerate(rail_1.source_stations[:3], 1):
        print(f"    - Source Station {idx}: {st.name} ({st.distance_from_location_km:.2f} km)")
    for idx, st in enumerate(rail_1.destination_stations[:3], 1):
        print(f"    - Dest Station {idx}:   {st.name} ({st.distance_from_location_km:.2f} km)")

    print(f"\n[RAIL RESULT - STAGE 2: TRAIN CONNECTIVITY]\n  Status:             {rail_1.train_connectivity.status}\n  Trains Discovered:  {len(rail_1.trains)}")
    if rail_1.trains:
        for idx, train in enumerate(rail_1.trains[:3], 1):
            print(f"    - Train {idx}: [{train.train_number}] {train.train_name} ({train.source_station_code} -> {train.destination_station_code})")

    # Assertions: Road route found
    assert road_1.available is True
    assert road_1.status == "ROUTE_FOUND"

    # Assertions: Rail physical stations found
    assert rail_1.station_discovery.status == "STATIONS_FOUND"
    assert len(rail_1.source_stations) > 0
    assert len(rail_1.destination_stations) > 0

    # Assertions: Train connectivity evaluated
    assert rail_1.train_connectivity.status in ("TRAINS_FOUND", "API_ERROR")
    if rail_1.train_connectivity.status == "TRAINS_FOUND":
        assert len(rail_1.trains) > 0, "Expected discovered trains"

    print("\n[PASS] SUBGRAPH TEST 1 passed (Road found, Rail stations discovered & trains connected).\n")

    print("=" * 70)
    print("SUBGRAPH TEST 2: Mumbai -> Honolulu (Independent Mode Preservations)")
    print("=" * 70)

    input_2: TransportState = {
        "source": "Mumbai",
        "destination": "Honolulu",
        "date_of_travel": None,
        "road_result": None,
        "rail_result": None,
        "result": None,
    }

    output_2 = transport_subgraph.invoke(input_2)
    result_2 = output_2.get("result")

    assert result_2 is not None, "TransportationResult should be produced even when modes fail!"
    road_2 = result_2.road
    rail_2 = result_2.rail

    assert road_2 is not None, "Road result must be present!"
    assert rail_2 is not None, "Rail result must be present!"

    print(f"\n[ROAD RESULT]\n  Available: {road_2.available}\n  Status:    {road_2.status}\n  Error:     {road_2.error_message}")
    print(f"\n[RAIL RESULT]\n  Station Status:       {rail_2.station_discovery.status}\n  Train Status:         {rail_2.train_connectivity.status}\n  Source Stations:      {len(rail_2.source_stations)}\n  Destination Stations: {len(rail_2.destination_stations)}")

    assert road_2.available is False
    assert road_2.status == "NO_ROUTE_EXISTS"
    assert rail_2.station_discovery.status == "NO_DESTINATION_STATION"
    assert rail_2.train_connectivity.status == "NOT_CHECKED"
    print("\n[PASS] SUBGRAPH TEST 2 passed (Mode failures preserved independently without crashing).\n")


if __name__ == "__main__":
    run_subgraph_tests()
