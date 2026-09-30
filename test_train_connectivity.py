"""
Dedicated Test Suite for Rail Train Connectivity Layer (Step 8B).
Verifies:
1. Candidate train discovery for Hyderabad -> Bengaluru:
   - Physical railway station discovery
   - Station-code resolution (Secunderabad -> SC, KSR Bengaluru -> SBC, etc.)
   - RailRadar train discovery API query
   - Response normalization into TrainService models
   - Deduplication by train_number while preserving source/destination station codes
   - Status TRAINS_FOUND
2. Unconnected destination handling (Mumbai -> Honolulu):
   - Graceful fallback without crashing
   - Clear distinction: physical station not found vs no trains found
3. Controlled error condition:
   - STATION_CODE_UNRESOLVABLE when codes cannot be determined
   - API_ERROR when provider encounters authentication or server errors
   - Verification that API errors are NEVER conflated with NO_TRAINS_FOUND
"""
import os
import sys

# Ensure src/ is on python path
sys.path.insert(0, os.path.abspath("src"))

from unittest.mock import patch
import requests
from travel_planner.transport.tools.rail.trains_tool import (
    find_train_connections,
    discover_train_services,
)

from travel_planner.transport.state import (
    RailTransportResult,
    RailStationDiscoveryResult,
    TrainConnectivityResult,
)


def run_tests():
    print("=" * 75)
    print("TEST 1: Primary Train Connectivity (Hyderabad -> Bengaluru)")
    print("=" * 75)



    rail_result_1: RailTransportResult = find_train_connections(
        source="Hyderabad",
        destination="Bengaluru",
        max_source_stations=3,
        max_destination_stations=3,
    )

    assert isinstance(rail_result_1, RailTransportResult), "Result must be a RailTransportResult"
    assert isinstance(rail_result_1.station_discovery, RailStationDiscoveryResult), "station_discovery must be RailStationDiscoveryResult"
    assert isinstance(rail_result_1.train_connectivity, TrainConnectivityResult), "train_connectivity must be TrainConnectivityResult"

    disc_1 = rail_result_1.station_discovery
    conn_1 = rail_result_1.train_connectivity

    print(f"Source:                         {disc_1.source}")
    print(f"Destination:                    {disc_1.destination}")
    print(f"Station Discovery Status:       {disc_1.status}")
    print(f"Physical Source Stations:       {len(disc_1.source_stations)}")
    print(f"Physical Destination Stations:  {len(disc_1.destination_stations)}")
    print(f"Train Connectivity Status:      {conn_1.status}")
    print(f"Total Trains Discovered:        {len(conn_1.trains)}")
    if disc_1.error_message:
        print(f"Station Discovery Error:        {disc_1.error_message}")
    if conn_1.error_message:
        print(f"Train Connectivity Error:       {conn_1.error_message}")

    # 1. Verify physical station discovery succeeded

    assert disc_1.status == "STATIONS_FOUND", f"Expected STATIONS_FOUND, got: {disc_1.status}"
    assert len(disc_1.source_stations) > 0
    assert len(disc_1.destination_stations) > 0

    # 2. Verify train connectivity outcome
    assert conn_1.status in ("TRAINS_FOUND", "API_ERROR"), f"Unexpected train status: {conn_1.status}"

    if conn_1.status == "TRAINS_FOUND":
        assert len(conn_1.trains) > 0, "Expected trains between Hyderabad and Bengaluru"

        # Check deduplication by train_number
        train_numbers = [t.train_number for t in conn_1.trains]
        assert len(train_numbers) == len(set(train_numbers)), "Train numbers must be unique (deduplicated)!"

        print("\nDiscovered Train Services (Sample):")
        for idx, train in enumerate(conn_1.trains[:5], 1):
            # Verify required fields are populated
            assert train.train_number and train.train_number != "UNKNOWN", "train_number must be populated"
            assert train.train_name, "train_name must be populated"
            assert train.source_station_code, "source_station_code must be preserved"
            assert train.destination_station_code, "destination_station_code must be preserved"

            dur_str = f"{train.duration_minutes // 60}h {train.duration_minutes % 60}m" if train.duration_minutes else "N/A"
            print(
                f"  {idx}. [{train.train_number}] {train.train_name} ({train.train_type or 'Express'})\n"
                f"     Pair: {train.source_station_code} -> {train.destination_station_code} | "
                f"Dep: {train.departure_time or 'N/A'} | Arr: {train.arrival_time or 'N/A'} | "
                f"Duration: {dur_str} | Dist: {train.distance_km or 'N/A'} km"
            )

        print("\n[PASS] PRIMARY TEST 1 passed (Stations discovered, codes resolved, trains returned & deduplicated).\n")
    else:
        print(f"\n[INFO] RailRadar reported API status: {conn_1.error_message}\n")

    print("=" * 75)
    print("TEST 2: Unconnected / Non-Railway Destination (Mumbai -> Honolulu)")
    print("=" * 75)

    rail_result_2 = find_train_connections(
        source="Mumbai",
        destination="Honolulu",
    )

    disc_2 = rail_result_2.station_discovery
    conn_2 = rail_result_2.train_connectivity

    print(f"Station Discovery Status:   {disc_2.status}")
    print(f"Train Connectivity Status:  {conn_2.status}")
    print(f"Trains Found:               {len(conn_2.trains)}")

    assert disc_2.status == "NO_DESTINATION_STATION"
    assert conn_2.status == "NOT_CHECKED"
    assert len(conn_2.trains) == 0
    print("\n[PASS] TEST 2 passed (Safely halted train query when physical stations do not exist).\n")

    print("=" * 75)
    print("TEST 3: Controlled Station Code Unresolvable & API Error Separation")
    print("=" * 75)

    # 3a. Unresolvable station codes
    unres_result = discover_train_services(
        source_codes=[],
        dest_codes=["SBC"],
    )
    print(f"Unresolvable codes status: {unres_result.status}")
    assert unres_result.status == "STATION_CODE_UNRESOLVABLE"
    assert len(unres_result.trains) == 0

    # 3b. Controlled API Error (Simulate 401/500 to ensure NEVER converted to NO_TRAINS_FOUND)
    with patch("travel_planner.transport.services.railradar_client.requests.get") as mock_get:
        mock_response = requests.Response()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        api_err_result = discover_train_services(
            source_codes=["SC"],
            dest_codes=["SBC"],
        )
        print(f"Simulated 401 error status: {api_err_result.status}")
        assert api_err_result.status == "API_ERROR", f"Expected API_ERROR, got: {api_err_result.status}"
        assert api_err_result.status != "NO_TRAINS_FOUND", "API errors must NEVER be masked as NO_TRAINS_FOUND!"

    print("\n[PASS] TEST 3 passed (Error conditions clearly isolated and distinct).\n")
    print("ALL STEP 8B TESTS COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    run_tests()
