from travel_planner.transport.tools.road.routes_tool import compute_road_route


def test_route(source: str, destination: str, label: str):
    print("\n" + "=" * 60)
    print(f"TEST: {label} ('{source}' -> '{destination}')")
    print("=" * 60)
    result = compute_road_route(source=source, destination=destination)
    print(f"Status:             {result.status}")
    print(f"Available:          {result.available}")
    print(f"Distance (km):      {result.distance_km}")
    print(f"Duration:           {result.duration_formatted}")
    if result.error_message:
        print(f"Error Message:      {result.error_message}")
    return result


def main():
    # 1. Valid driving route
    test_route("Hyderabad", "Bengaluru", "Valid Route")

    # 2. Unresolvable source
    test_route("Xyzabc999NonExistentSource", "Bengaluru", "Unresolvable Source")

    # 3. Unresolvable destination
    test_route("Hyderabad", "Xyzabc999NonExistentDest", "Unresolvable Destination")

    # 4. No driving route (across ocean: Mumbai to London / Honolulu)
    test_route("Mumbai", "Honolulu", "No Driving Route (Overseas)")


if __name__ == "__main__":
    main()
