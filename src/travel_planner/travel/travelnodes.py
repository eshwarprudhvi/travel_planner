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


# --- Date of Travel Workflow ---

class DateOutput(BaseModel):
    date_of_travel: str | None = Field(
        default=None,
        description="The travel date, date range, or time period mentioned by the user (e.g. 'October 15', 'next month'), or None if not mentioned"
    )


DATE_PROMPT = """You are an expert travel assistant. Analyze the user's travel request and extract the date of travel, date range, or time period they plan to travel.

Guidelines:
- Extract the date or time period as stated by the user (for example: "October 15", "next month", "tomorrow", "first week of December", "10th to 15th Nov").
- Do NOT convert or normalize relative dates into concrete dates yet (e.g. keep "next month" as "next month").
- Do NOT extract trip duration or number of days (e.g. in "I want to travel for 5 days", 5 days is the duration, not the date of travel).
- If no date or time period is mentioned (for example, "Take me to Goa" or "I want to travel somewhere"), return null / None.

User Request: {prompt}
"""


# routers
def route_date(state: TravelState) -> str:
    """
    Examines state['date_of_travel'] and routes to:
    - 'ask_date' if date_of_travel is missing or None
    - 'continue' if date_of_travel exists
    """
    date_of_travel = state.get("date_of_travel")
    if date_of_travel:
        return "continue"
    return "ask_date"


# nodes
@traceable(run_type="chain", name="extract_date")
def extract_date(state: TravelState) -> dict:
    """
    Extracts the travel date or time period from state['prompt']
    and updates state['date_of_travel'].
    """
    prompt = state.get("prompt", "") or ""
    model_with_structured_output = gemini_llm.with_structured_output(DateOutput)
    result: DateOutput = model_with_structured_output.invoke(
        DATE_PROMPT.format(prompt=prompt)
    )

    return {"date_of_travel": result.date_of_travel}


@traceable(run_type="chain", name="ask_date")
def ask_date(state: TravelState) -> dict:
    """
    Prompts the user to provide their travel date when none was extracted,
    then updates state['prompt'] with the user's response so it can be re-extracted.
    """
    user_response = interrupt("When would you like to travel?")
    return {"prompt": user_response}


# --- Number of Days Workflow ---

class NumberOfDaysOutput(BaseModel):
    number_of_days: int | None = Field(
        default=None,
        description="The explicitly stated number of days or trip duration as an integer, or None if not mentioned"
    )


NUMBER_OF_DAYS_PROMPT = """You are an expert travel assistant. Analyze the user's travel request and extract the explicitly stated duration or number of days for the trip.

Guidelines:
- Extract ONLY explicitly stated trip duration (for example: "5 day trip" -> 5, "stay for 3 days" -> 3, "2 days" -> 2, "a week" -> 7).
- Return an integer value representing the number of days.
- Do NOT calculate the duration by subtracting dates from a date range (for example, in "I'll travel from October 10 to October 15", do not compute 5 days; return null / None).
- If no explicit duration or number of days is stated (for example, "Plan a trip to Goa" or "I want to visit Paris in October"), return null / None.

User Request: {prompt}
"""


# routers
def route_number_of_days(state: TravelState) -> str:
    """
    Examines state['number_of_days'] and routes to:
    - 'ask_number_of_days' if number_of_days is missing, None, or <= 0
    - 'continue' if number_of_days exists
    """
    number_of_days = state.get("number_of_days")
    if number_of_days and number_of_days > 0:
        return "continue"
    return "ask_number_of_days"


# nodes
@traceable(run_type="chain", name="extract_number_of_days")
def extract_number_of_days(state: TravelState) -> dict:
    """
    Extracts the explicitly stated trip duration in days from state['prompt']
    and updates state['number_of_days'].
    """
    prompt = state.get("prompt", "") or ""
    model_with_structured_output = gemini_llm.with_structured_output(NumberOfDaysOutput)
    result: NumberOfDaysOutput = model_with_structured_output.invoke(
        NUMBER_OF_DAYS_PROMPT.format(prompt=prompt)
    )

    return {"number_of_days": result.number_of_days}


@traceable(run_type="chain", name="ask_number_of_days")
def ask_number_of_days(state: TravelState) -> dict:
    """
    Prompts the user to provide the number of days when none was extracted,
    then updates state['prompt'] with the user's response so it can be re-extracted.
    """
    user_response = interrupt("How many days would you like the trip to be?")
    return {"prompt": user_response}


# --- Budget Workflow ---

class BudgetOutput(BaseModel):
    budget: int | None = Field(
        default=None,
        description="The maximum or intended trip budget as an integer (e.g. ₹30,000 -> 30000, 50k -> 50000), or None if not mentioned"
    )


BUDGET_PROMPT = """You are an expert travel assistant. Analyze the user's travel request and extract the monetary budget they plan to spend on the trip.

Guidelines:
- Extract the monetary budget as an integer number.
- Normalize obvious shorthand and currency symbols:
  * "₹30,000" or "30000 rs" or "30,000" -> 30000
  * "30k" or "30K" -> 30000
  * "50k" or "50K" -> 50000
  * "1 lakh" or "1L" -> 100000
  * "$500" -> 500 (extract the numeric value 500 without converting currencies)
- If no monetary budget is stated (for example, "Plan a trip to Goa for 5 days"), return null / None.

User Request: {prompt}
"""


# routers
def route_budget(state: TravelState) -> str:
    """
    Examines state['budget'] and routes to:
    - 'ask_budget' if budget is missing, None, or <= 0
    - 'continue' if budget exists
    """
    budget = state.get("budget")
    if budget and budget > 0:
        return "continue"
    return "ask_budget"


# nodes
@traceable(run_type="chain", name="extract_budget")
def extract_budget(state: TravelState) -> dict:
    """
    Extracts the monetary budget from state['prompt']
    and updates state['budget'].
    """
    prompt = state.get("prompt", "") or ""
    model_with_structured_output = gemini_llm.with_structured_output(BudgetOutput)
    result: BudgetOutput = model_with_structured_output.invoke(
        BUDGET_PROMPT.format(prompt=prompt)
    )

    return {"budget": result.budget}


@traceable(run_type="chain", name="ask_budget")
def ask_budget(state: TravelState) -> dict:
    """
    Prompts the user to provide their budget when none was extracted,
    then updates state['prompt'] with the user's response so it can be re-extracted.
    """
    user_response = interrupt("What is your budget for the trip?")
    return {"prompt": user_response}


# --- Transportation Workflow ---

@traceable(run_type="chain", name="transportation_workflow")
def transportation_workflow(state: TravelState) -> dict:
    """
    Invokes the independent Transportation Subgraph using the parent state's
    'source' and first 'destination', then saves the structured result
    into state['transportation'].
    """
    from travel_planner.transport.graph import create_transport_graph
    from travel_planner.transport.state import TransportState

    source = state.get("source") or ""
    destinations = state.get("destination", [])
    destination = destinations[0] if destinations else ""

    transport_subgraph = create_transport_graph()
    subgraph_input: TransportState = {
        "source": source,
        "destination": destination,
        "road_result": None,
    }

    subgraph_output = transport_subgraph.invoke(subgraph_input)
    road_result = subgraph_output.get("road_result")

    return {
        "transportation": {
            "road_result": road_result
        }
    }