"""
Transportation Decision Agent (Step 9).

This is the first LLM-based reasoning layer in transportation.
It consumes ONLY structured TransportationResult facts and produces a
structured TransportationRecommendation.

Strict Rules:
- The LLM receives pre-collected TransportationResult data.
- The LLM has NO direct access to external transportation tools (no ORS, no Overpass, no RailRadar, no Qrail).
- The LLM is strictly prohibited from inventing prices, train numbers, routes, schedules, or air/water travel.
- If information is missing, it must be explicitly noted under limitations.
- If the LLM call fails, the failure is caught and a DECISION_ERROR recommendation is returned without altering TransportationResult.
"""
from typing import Optional
from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import traceable

from travel_planner.llm import gemini_llm
from travel_planner.transport.state import (
    TransportationResult,
    TransportationRecommendation,
)


TRANSPORT_DECISION_SYSTEM_PROMPT = """You are an expert, objective transportation decision assistant.
Your job is to evaluate factual transportation options for a traveler based EXCLUSIVELY on the provided TransportationResult JSON data.

STRICT CONSTRAINTS & NEGATIVE CONSTRAINTS:
1. Grounding: Every claim, train number, duration, or distance you state MUST come directly from the provided factual data.
2. DO NOT INVENT OR ESTIMATE:
   - NEVER invent or guess ticket fares, prices, or budget calculations (pricing is NOT provided in the input).
   - NEVER invent train numbers, train names, departure/arrival times, or schedules not in the data.
   - NEVER suggest or invent flights, airlines, buses, ferries, or water travel (these modalities are not supported).
   - NEVER invent road driving routes, alternative highways, or distances if road routing failed.
   - NEVER invent seat availability, coach classes, or live delay status if enrichment is missing or failed.
3. MISSING INFORMATION:
   - If pricing/cost information is missing (it always is in this milestone), explicitly add: "Ticket prices and fares are not available in current data" to limitations and unsupported_or_missing_info.
   - If train enrichment (live running status or detailed schedule) is missing or in error, explicitly state that in limitations and unsupported_or_missing_info.
4. OUTCOME & RECOMMENDATION RULES:
   - If both Road and Rail are available, compare them objectively (e.g. travel duration, directness, ease of travel) and recommend the best option ("road", "rail", or "both").
   - If only Road is available, set recommended_option="road", mark rail as available=False with the factual reason, and explain why road is the only viable option.
   - If only Rail has trains available, set recommended_option="rail", mark road as available=False with the factual reason, and explain why rail is the viable option.
   - If neither Road nor Rail has viable services (e.g., overseas destination, unresolvable locations, no trains found, or API errors), set:
       status="NO_VIABLE_OPTION"
       recommended_option="none"
       primary_recommendation_reason explaining factually that no viable transport options were discovered.
"""


def _format_facts_for_prompt(
    transport_result: TransportationResult,
    date_of_travel: Optional[str] = None,
) -> str:
    """Serializes TransportationResult into an explicit, readable factual summary."""
    lines = []
    lines.append(f"Date of Travel: {date_of_travel or 'Not specified'}")

    # Road facts
    lines.append("\n--- ROAD TRANSPORTATION FACTS ---")
    if transport_result.road:
        r = transport_result.road
        lines.append(f"Status: {r.status}")
        lines.append(f"Available: {r.available}")
        lines.append(f"Source: {r.source}")
        lines.append(f"Destination: {r.destination}")
        lines.append(f"Distance: {r.distance_km} km" if r.distance_km is not None else "Distance: Not available")
        lines.append(f"Duration: {r.duration_formatted}" if r.duration_formatted else "Duration: Not available")
        if r.error_message:
            lines.append(f"Error / Failure Details: {r.error_message}")
    else:
        lines.append("Road data: Not evaluated / None")

    # Rail facts
    lines.append("\n--- RAIL TRANSPORTATION FACTS ---")
    if transport_result.rail:
        rail = transport_result.rail
        disc = rail.station_discovery
        conn = rail.train_connectivity
        enrich = rail.train_enrichment

        lines.append(f"Physical Station Discovery Status: {disc.status}")
        lines.append(f"Source Stations Found ({len(disc.source_stations)}):")
        for s in disc.source_stations[:5]:
            lines.append(f"  - {s.name} ({s.distance_from_location_km:.2f} km away)")

        lines.append(f"Destination Stations Found ({len(disc.destination_stations)}):")
        for s in disc.destination_stations[:5]:
            lines.append(f"  - {s.name} ({s.distance_from_location_km:.2f} km away)")

        lines.append(f"Train Connectivity Status: {conn.status}")
        if conn.error_message:
            lines.append(f"Train Discovery Error: {conn.error_message}")

        lines.append(f"Scheduled Trains Found ({len(conn.trains)}):")
        for t in conn.trains:
            lines.append(
                f"  - Train #{t.train_number} ({t.train_name}): "
                f"{t.source_station_code} ({t.departure_time or 'N/A'}) -> "
                f"{t.destination_station_code} ({t.arrival_time or 'N/A'}), "
                f"Duration: {t.duration_minutes} mins, Distance: {t.distance_km} km, "
                f"Runs: {t.run_days or 'N/A'}"
            )

        if enrich:
            lines.append(f"Train Enrichment Status: {enrich.status}")
            if enrich.error_message:
                lines.append(f"Enrichment Provider Message: {enrich.error_message}")
        else:
            lines.append("Train Enrichment: Not performed")
    else:
        lines.append("Rail data: Not evaluated / None")

    return "\n".join(lines)


@traceable(run_type="chain", name="decide_transportation")
def decide_transportation(
    transport_result: TransportationResult,
    date_of_travel: Optional[str] = None,
    llm=None,
) -> TransportationRecommendation:
    """
    Executes the Transportation Decision Agent.
    Evaluates pre-collected TransportationResult facts using structured LLM reasoning.
    Does NOT call any external transportation APIs.
    """
    model = llm or gemini_llm

    factual_content = _format_facts_for_prompt(transport_result, date_of_travel)

    messages = [
        SystemMessage(content=TRANSPORT_DECISION_SYSTEM_PROMPT),
        HumanMessage(content=f"Here are the collected transportation facts:\n\n{factual_content}\n\nProduce your structured TransportationRecommendation."),
    ]

    try:
        structured_model = model.with_structured_output(TransportationRecommendation)
        recommendation: TransportationRecommendation = structured_model.invoke(messages)

        # Sanity check: Ensure valid model returned
        if not isinstance(recommendation, TransportationRecommendation):
            return TransportationRecommendation(
                status="DECISION_ERROR",
                primary_recommendation_reason="Decision agent returned invalid format.",
                error_message="Model output did not conform to TransportationRecommendation schema.",
                limitations=["Output validation failed"],
            )

        return recommendation

    except Exception as e:
        # Graceful failure preservation: Never raise or discard TransportationResult
        return TransportationRecommendation(
            status="DECISION_ERROR",
            primary_recommendation_reason="Decision agent encountered an error during reasoning.",
            error_message=f"{type(e).__name__}: {str(e)}",
            limitations=["LLM decision agent execution failed; raw transportation facts remain intact."],
        )
