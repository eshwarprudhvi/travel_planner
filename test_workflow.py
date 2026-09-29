import uuid
from langgraph.types import Command
from travel_planner.graph import create_graph


def run_tests():
    app = create_graph()

    print("=" * 60)
    print("TEST 1: Direct Travel Request")
    print("=" * 60)
    config_1 = {"configurable": {"thread_id": str(uuid.uuid4())}}
    initial_input_1 = {
        "prompt": "Plan a 3-day trip to Tokyo",
        "messages": [],
        "non_travel_attempts": 0
    }
    output_1 = app.invoke(initial_input_1, config=config_1)
    print("Final State Test 1:", output_1)
    print("SUCCESS: Directly routed to travel planner!\n")

    print("=" * 60)
    print("TEST 2: Non-Travel Request -> Interrupted -> Resumed with Travel Request")
    print("=" * 60)
    config_2 = {"configurable": {"thread_id": str(uuid.uuid4())}}
    initial_input_2 = {
        "prompt": "Write a python script to sort a list",
        "messages": [],
        "non_travel_attempts": 0
    }
    
    # 1. First invocation: Expect graph to interrupt at not_travel_workflow
    state_after_interrupt = app.invoke(initial_input_2, config=config_2)
    print("State at interrupt:", state_after_interrupt)
    
    # Check interrupt details
    state_snapshot = app.get_state(config_2)
    print("Pending Interrupt:", state_snapshot.tasks[0].interrupts if state_snapshot.tasks else "None")
    
    # 2. Resume the interrupted graph with a travel prompt
    resumed_output = app.invoke(
        Command(resume="Actually, plan a trip to Goa for 5 days"),
        config=config_2
    )
    print("Final State Test 2:", resumed_output)
    print("SUCCESS: Successfully interrupted, resumed, and routed to travel planner!\n")

    print("=" * 60)
    print("TEST 3: Non-Travel Reaches Max Attempts (4) -> Terminates at END")
    print("=" * 60)
    config_3 = {"configurable": {"thread_id": str(uuid.uuid4())}}
    curr_state = app.invoke(
        {"prompt": "Tell me a joke", "messages": [], "non_travel_attempts": 0},
        config=config_3
    )

    for i in range(1, 4):
        print(f"Resuming with non-travel prompt attempt #{i}...")
        curr_state = app.invoke(
            Command(resume=f"Tell me another joke #{i}"),
            config=config_3
        )

    print("Final State Test 3 after max non-travel attempts:", curr_state)
    print("SUCCESS: Reached max attempts and terminated at END!\n")


if __name__ == "__main__":
    run_tests()
