from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from typing import Literal
from .state import AgentState
from langgraph.types import interrupt
from langsmith import traceable
from .llm import groq_llm, gemini_llm

prompt_template = """

You are an expert in understanding user intents. Analyze the following prompt and classify it as either "TRAVEL" or "NOT_TRAVEL".

Prompt: {prompt}

Return ONLY one word: TRAVEL or NOT_TRAVEL
"""

class IntentOutput(BaseModel):
    intent: Literal["TRAVEL", "NOT_TRAVEL"]


#routers

def route_to_planner_or_not(state: AgentState):
    if state.get("non_travel_attempts", 0) >= 4:
        return "END"
    elif state.get("intent") == "TRAVEL":
        return "travel_planner_workflow"
    else:
        return "not_travel_workflow"


##nodes 

@traceable(run_type="chain", name="classify_intent")
def classify_intent(state: AgentState):
    """
    Classifies the intent of the user's prompt as TRAVEL or NOT_TRAVEL
    """
    model_with_structured_output = gemini_llm.with_structured_output(IntentOutput)

    result = model_with_structured_output.invoke(prompt_template.format(prompt=state["prompt"]))

    print("---->>>>>", result)

    return {"intent": result.intent}

@traceable(run_type="chain", name="not_travel_workflow")
def not_travel_workflow(state: AgentState):
    
    user_message = interrupt(
        "I can only help with travel-related requests. "
        "What travel-related task can I help you with?"
    )
    return {
        "messages": [HumanMessage(content=user_message)],
        "non_travel_attempts": state.get("non_travel_attempts", 0) + 1,
        "prompt": user_message
    }

@traceable(run_type="chain", name="travel_planner_workflow")
def travel_planner_workflow(state: AgentState):
    print("Executing travel_planner_workflow for prompt:", state.get("prompt"))
    return {}
    


if __name__ == "__main__":
    print("Testing 'plan a trip to goa':")
    classify_intent({"prompt": "plan a trip to goa"})

    print("Testing 'hi how are you':")
    classify_intent({"prompt": "hi how are you"})


    
