from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from travel_planner.nodes import classify_intent, not_travel_workflow, route_to_planner_or_not, travel_planner_workflow
from travel_planner.state import AgentState

def create_graph(checkpointer=None):
    workflow = StateGraph(AgentState)

    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("not_travel_workflow", not_travel_workflow)
    workflow.add_node("travel_planner_workflow", travel_planner_workflow)
    
    workflow.add_edge(START, "classify_intent")
    workflow.add_conditional_edges(
        "classify_intent",
        route_to_planner_or_not,
        {
            "travel_planner_workflow": "travel_planner_workflow",
            "not_travel_workflow": "not_travel_workflow",
            "END": END
        }
    )
    workflow.add_edge("not_travel_workflow", "classify_intent")
    workflow.add_edge("travel_planner_workflow", END)

    if checkpointer is None:
        checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)