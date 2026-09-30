from typing import Literal, Optional
from typing_extensions import TypedDict

from travel_planner.transport.state import (
    TransportationResult,
    TransportationRecommendation,
)


class TravelState(TypedDict):
    prompt: Optional[str]
    source: Optional[str]
    destination: list[str]
    date_of_travel: Optional[str]    
    number_of_days: Optional[int]
    mode_of_travel: Optional[str]    
    budget: Optional[int]
    transportation: Optional[TransportationResult]
    transportation_recommendation: Optional[TransportationRecommendation]
    accommodation_type: Optional[str]
    itinerary: Optional[str]


    
    
    
    