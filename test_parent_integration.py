import uuid
from travel_planner.travel.travelgraph import create_travel_graph


def run_tests():
    app = create_travel_graph()

    print("=" * 70)
    print("TEST 1: Valid Road Route in Parent Graph (Hyderabad -> Bengaluru)")
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
    print(f"Transportation: {transportation}")
    
    road_result = transportation.get("road_result") if transportation else None
    assert road_result is not None, "Road route result should be populated in transportation!"
    print(f"Road Available: {road_result.available}")
    print(f"Road Status:    {road_result.status}")
    print(f"Distance (km):  {road_result.distance_km}")
    print(f"Duration:       {road_result.duration_formatted}")

    assert road_result.available is True
    assert road_result.status == "ROUTE_FOUND"
    print("\n[PASS] SUCCESS: Test 1 passed (Road route found and stored in parent state).\n")

    print("=" * 70)
    print("TEST 2: No Road Route Exists (Mumbai -> Honolulu)")
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
    }

    final_state_2 = app.invoke(initial_input_2, config=config_2)

    print("\n--- Final TravelState (Test 2) ---")
    print(f"Destination:    {final_state_2.get('destination')}")
    print(f"Source:         {final_state_2.get('source')}")
    
    transportation_2 = final_state_2.get("transportation")
    road_result_2 = transportation_2.get("road_result") if transportation_2 else None
    assert road_result_2 is not None, "Road route result should be populated even on routing failure!"
    print(f"Road Available: {road_result_2.available}")
    print(f"Road Status:    {road_result_2.status}")
    print(f"Error Message:  {road_result_2.error_message}")

    assert road_result_2.available is False
    assert road_result_2.status == "NO_ROUTE_EXISTS"
    print("\n[PASS] SUCCESS: Test 2 passed (NO_ROUTE_EXISTS cleanly preserved without crashing).\n")


if __name__ == "__main__":
    run_tests()
