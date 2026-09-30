"""
Standalone test script for the Rail Transportation Station Discovery Capability (Step 5).
Verifies:
1. Candidate railway station discovery near source and destination (Hyderabad -> Bengaluru).
2. Appropriate domain status when no railway stations exist near a location (e.g. Honolulu -> Bengaluru).
"""
from travel_planner.transport.tools.rail.station_tool import find_nearby_railway_stations


def run_tests():
    print("=" * 70)
    print("TEST 1: Rail Station Discovery (Hyderabad -> Bengaluru)")
    print("=" * 70)

    result_1 = find_nearby_railway_stations(
        source="Hyderabad",
        destination="Bengaluru",
        radius_km=50.0,
        limit=5,
    )

    print(f"Source:       {result_1.source}")
    print(f"Destination:  {result_1.destination}")
    print(f"Status:       {result_1.status}")
    print(f"Error:        {result_1.error_message}")

    print("\nCandidate Stations near Source (Hyderabad):")
    for idx, station in enumerate(result_1.source_stations, 1):
        print(f"  {idx}. {station.name} [{station.railway_type}] - {station.distance_from_location_km:.2f} km away (Lat: {station.latitude:.4f}, Lon: {station.longitude:.4f})")

    print("\nCandidate Stations near Destination (Bengaluru):")
    for idx, station in enumerate(result_1.destination_stations, 1):
        print(f"  {idx}. {station.name} [{station.railway_type}] - {station.distance_from_location_km:.2f} km away (Lat: {station.latitude:.4f}, Lon: {station.longitude:.4f})")

    assert result_1.status == "STATIONS_FOUND", f"Expected STATIONS_FOUND but got {result_1.status}"
    assert len(result_1.source_stations) > 0, "Expected at least one station near Hyderabad"
    assert len(result_1.destination_stations) > 0, "Expected at least one station near Bengaluru"
    print("\n[PASS] SUCCESS: Test 1 passed (Stations found near both source and destination).\n")

    print("=" * 70)
    print("TEST 2: Location with No Railway Stations (Honolulu -> Bengaluru)")
    print("=" * 70)

    result_2 = find_nearby_railway_stations(
        source="Honolulu",
        destination="Bengaluru",
        radius_km=50.0,
        limit=5,
    )

    print(f"Source:       {result_2.source}")
    print(f"Destination:  {result_2.destination}")
    print(f"Status:       {result_2.status}")
    print(f"Error:        {result_2.error_message}")
    print(f"Source Stations Count:      {len(result_2.source_stations)}")
    print(f"Destination Stations Count: {len(result_2.destination_stations)}")

    assert result_2.status == "NO_SOURCE_STATION", f"Expected NO_SOURCE_STATION but got {result_2.status}"
    assert len(result_2.source_stations) == 0, "Honolulu should have no mainline railway stations within 50 km"
    assert len(result_2.destination_stations) > 0, "Bengaluru should have stations"
    print("\n[PASS] SUCCESS: Test 2 passed (NO_SOURCE_STATION cleanly identified without throwing an exception).\n")


if __name__ == "__main__":
    run_tests()
