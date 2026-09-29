from langgraph.types import interrupt
from langsmith import traceable
from pydantic import BaseModel, Field
from travel_planner.llm import gemini_llm
from .travelState import TravelState


class DestinationOutput(BaseModel):
    destinations: list[str] = Field(
        default_factory=list,
        description="List of destination names explicitly mentioned by the user to visit or travel to"
    )


DESTINATION_PROMPT = """You are an expert travel assistant. Analyze the user's travel request and extract all destination names they explicitly want to visit.

Guidelines:
- Extract ONLY the destinations the user intends to travel to or visit.
- Do NOT include origin, departure, or source locations (for example, in "Plan a trip from Hyderabad to Goa", "Goa" is the destination and "Hyderabad" is the departure/source point).
- If no destination is explicitly mentioned (for example, "I want to travel somewhere for 5 days"), return an empty list.
- Return clean, properly capitalized city, region, or country names (e.g., ["Goa"], ["Paris", "Rome", "Barcelona"]).

User Request: {prompt}
"""


# routers
def route_destination(state: TravelState) -> str:
    """
    Examines state['destination'] and routes to:
    - 'ask_destination' if no destination was found (len == 0)
    - 'ask_choose_destination' if multiple destinations were found (len > 1)
    - 'validate_destination' if a single destination was found (len == 1)
    """
    destinations = state.get("destination", [])
    if not destinations:
        return "ask_destination"
    elif len(destinations) > 1:
        return "ask_choose_destination"
    else:
        return "validate_destination"


# nodes
@traceable(run_type="chain", name="extract_destination")
def extract_destination(state: TravelState) -> dict:
    """
    Extracts all destination names explicitly mentioned in state['prompt']
    and updates state['destination'].
    """
    prompt = state.get("prompt", "") or ""
    model_with_structured_output = gemini_llm.with_structured_output(DestinationOutput)
    result: DestinationOutput = model_with_structured_output.invoke(
        DESTINATION_PROMPT.format(prompt=prompt)
    )

    return {"destination": result.destinations}


@traceable(run_type="chain", name="ask_destination")
def ask_destination(state: TravelState) -> dict:
    """
    Prompts the user to provide a destination when none was extracted,
    then updates state['prompt'] with the user's response so it can be re-extracted.
    """
    user_response = interrupt("Where would you like to travel?")
    return {"prompt": user_response}


@traceable(run_type="chain", name="ask_choose_destination")
def ask_choose_destination(state: TravelState) -> dict:
    """
    Prompts the user to choose one destination when multiple were mentioned,
    then updates state['prompt'] with the user's response so it can be re-extracted.
    """
    destinations = state.get("destination", [])
    if len(destinations) == 2:
        dest_str = " and ".join(destinations)
    elif len(destinations) > 2:
        dest_str = ", ".join(destinations[:-1]) + f", and {destinations[-1]}"
    else:
        dest_str = destinations[0] if destinations else ""

    user_response = interrupt(
        f"You mentioned {dest_str}. Which destination would you like to plan the trip for?"
    )
    return {"prompt": user_response}


@traceable(run_type="chain", name="validate_destination")
def validate_destination(state: TravelState) -> dict:
    """
    Placeholder node for the destination validation step.
    Receives single destination (real or invalid) to be validated in future step.
    """
    return {}


# --- Source Workflow ---

class SourceOutput(BaseModel):
    source: str | None = Field(
        default=None,
        description="The starting, departure, or origin location explicitly mentioned by the user, or None if not mentioned"
    )


SOURCE_PROMPT = """You are an expert travel assistant. Analyze the user's travel request and extract the starting, departure, or origin location they are traveling from.

Guidelines:
- Extract ONLY the origin, departure, or starting location (for example, in "Travel from Hyderabad to Goa", "Hyderabad" is the source and "Goa" is the destination).
- Do NOT extract destination locations as the source.
- If no starting or departure location is mentioned (for example, "Plan a trip to Goa" or "I want to visit Paris"), return null / None.
- Return a clean, properly capitalized city, region, or country name (e.g., "Hyderabad", "Bangalore").

User Request: {prompt}
"""


# routers
def route_source(state: TravelState) -> str:
    """
    Examines state['source'] and routes to:
    - 'ask_source' if source is missing or None
    - 'continue' if a source exists
    """
    source = state.get("source")
    if source:
        return "continue"
    return "ask_source"


# nodes
@traceable(run_type="chain", name="extract_source")
def extract_source(state: TravelState) -> dict:
    """
    Extracts the origin/starting location from state['prompt']
    and updates state['source'].
    """
    prompt = state.get("prompt", "") or ""
    model_with_structured_output = gemini_llm.with_structured_output(SourceOutput)
    result: SourceOutput = model_with_structured_output.invoke(
        SOURCE_PROMPT.format(prompt=prompt)
    )

    return {"source": result.source}


@traceable(run_type="chain", name="ask_source")
def ask_source(state: TravelState) -> dict:
    """
    Prompts the user to provide their starting location when none was extracted,
    then updates state['prompt'] with the user's response so it can be re-extracted.
    """
    user_response = interrupt("Where will you be traveling from?")
    return {"prompt": user_response}