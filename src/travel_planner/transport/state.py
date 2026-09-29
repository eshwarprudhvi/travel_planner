from typing import Literal, Optional
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class RoadRouteResult(BaseModel):
    available: bool = Field(
        default=False,
        description="Whether a viable road route was found between source and destination"
    )
    source: str = Field(
        ...,
        description="Origin location as provided to the routing service"
    )
    destination: str = Field(
        ...,
        description="Destination location as provided to the routing service"
    )
    distance_km: Optional[float] = Field(
        default=None,
        description="Total driving distance in kilometers"
    )
    duration_formatted: Optional[str] = Field(
        default=None,
        description="Human-readable driving duration (e.g. '11 hours 45 mins')"
    )
    duration_seconds: Optional[int] = Field(
        default=None,
        description="Total driving duration in seconds"
    )
    status: Literal[
        "ROUTE_FOUND",
        "NO_ROUTE_EXISTS",
        "SOURCE_UNRESOLVABLE",
        "DESTINATION_UNRESOLVABLE",
        "API_ERROR",
    ] = Field(
        ...,
        description="Outcome of the road route query"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Details of any error or failure (authentication, network, etc.)"
    )


class TransportState(TypedDict):
    source: str
    destination: str
    road_result: Optional[RoadRouteResult]
