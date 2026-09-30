from typing import Any, Literal, Optional
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


class RailwayStation(BaseModel):
    name: str = Field(
        ...,
        description="Name of the railway station"
    )
    latitude: float = Field(
        ...,
        description="Latitude coordinate of the railway station"
    )
    longitude: float = Field(
        ...,
        description="Longitude coordinate of the railway station"
    )
    railway_type: str = Field(
        ...,
        description="OSM railway tag (e.g. 'station' or 'halt')"
    )
    distance_from_location_km: float = Field(
        ...,
        description="Direct distance in kilometers from the query location"
    )


class TrainService(BaseModel):
    """
    Domain-level model for a scheduled train service operating between two stations.
    """
    train_number: str = Field(
        ...,
        description="Official train number identifier (e.g. '12785')"
    )
    train_name: str = Field(
        ...,
        description="Name of the train (e.g. 'Kacheguda Express')"
    )
    train_type: Optional[str] = Field(
        default=None,
        description="Train classification/type (e.g. 'Superfast', 'Express', 'Vande Bharat')"
    )
    source_station_code: str = Field(
        ...,
        description="Departure railway station code (e.g. 'SC' or 'KCG')"
    )
    destination_station_code: str = Field(
        ...,
        description="Arrival railway station code (e.g. 'SBC' or 'YPR')"
    )
    source_station_name: Optional[str] = Field(
        default=None,
        description="Name of departure railway station"
    )
    destination_station_name: Optional[str] = Field(
        default=None,
        description="Name of arrival railway station"
    )
    departure_time: Optional[str] = Field(
        default=None,
        description="Scheduled departure time (e.g. '06:00' or '06:00:00')"
    )
    arrival_time: Optional[str] = Field(
        default=None,
        description="Scheduled arrival time (e.g. '14:30' or '14:30:00')"
    )
    duration_minutes: Optional[int] = Field(
        default=None,
        description="Total journey duration in minutes"
    )
    distance_km: Optional[float] = Field(
        default=None,
        description="Total journey distance in kilometers"
    )
    run_days: Optional[list[str]] = Field(
        default=None,
        description="Days of the week the train operates (e.g. ['Mon', 'Tue', ...])"
    )


class RailStationDiscoveryResult(BaseModel):
    """
    Domain-level model for railway station discovery near source and destination.
    Represents physical station presence, NOT operational train service availability.
    """
    source: str = Field(
        ...,
        description="Source location name"
    )
    destination: str = Field(
        ...,
        description="Destination location name"
    )
    source_stations: list[RailwayStation] = Field(
        default_factory=list,
        description="Candidate physical railway stations near the source"
    )
    destination_stations: list[RailwayStation] = Field(
        default_factory=list,
        description="Candidate physical railway stations near the destination"
    )
    status: Literal[
        "STATIONS_FOUND",
        "NO_SOURCE_STATION",
        "NO_DESTINATION_STATION",
        "NO_STATIONS_FOUND",
        "API_ERROR",
    ] = Field(
        ...,
        description="Outcome of physical station discovery"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Details of any error or failure (geocoding, network, Overpass error, etc.)"
    )


class TrainConnectivityResult(BaseModel):
    """
    Domain-level model for scheduled train service connectivity.
    Answers: Are there actual train services operating between candidate stations?
    (Placeholder boundary for future train API milestone; NOT populated in Step 8A).
    """
    source_station_code: Optional[str] = Field(
        default=None,
        description="Departure railway station code"
    )
    destination_station_code: Optional[str] = Field(
        default=None,
        description="Arrival railway station code"
    )
    trains: list[TrainService] = Field(
        default_factory=list,
        description="Scheduled train services operating between stations"
    )
    status: Literal[
        "NOT_CHECKED",
        "TRAINS_FOUND",
        "NO_TRAINS_FOUND",
        "STATION_CODE_UNRESOLVABLE",
        "API_ERROR",
    ] = Field(
        default="NOT_CHECKED",
        description="Outcome of train connectivity search"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Details of any error during train discovery"
    )


class TrainDetails(BaseModel):
    """
    Train details metadata enriched by Qrail.
    Treats Qrail schema as provisional/unverified without asserting speculative fields.
    """
    train_number: str = Field(
        ...,
        description="Official Indian Railways train number"
    )
    status: Literal["SUCCESS", "NOT_FOUND", "API_ERROR"] = Field(
        ...,
        description="Outcome of train details lookup"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if lookup failed"
    )
    provisional_details: Optional[dict[str, Any]] = Field(
        default=None,
        description="Raw or provisional details response from provider"
    )


class TrainRunningStatus(BaseModel):
    """
    Train running status enriched by Qrail.
    Treats Qrail schema as provisional/unverified without asserting speculative fields.
    """
    train_number: str = Field(
        ...,
        description="Official Indian Railways train number"
    )
    status: Literal["SUCCESS", "NOT_FOUND", "API_ERROR"] = Field(
        ...,
        description="Outcome of running status lookup"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if lookup failed"
    )
    provisional_running_status: Optional[dict[str, Any]] = Field(
        default=None,
        description="Raw or provisional running status response from provider"
    )


class TrainEnrichment(BaseModel):
    """
    Aggregates per-train enrichment (details and live running status) from Qrail.
    """
    train_number: str = Field(
        ...,
        description="Official Indian Railways train number"
    )
    details: Optional[TrainDetails] = Field(
        default=None,
        description="Train schedule/static details from enrichment provider"
    )
    running_status: Optional[TrainRunningStatus] = Field(
        default=None,
        description="Live running status from enrichment provider"
    )
    status: Literal["ENRICHED", "PARTIALLY_ENRICHED", "FAILED"] = Field(
        ...,
        description="Combined enrichment status for this train"
    )


class TrainEnrichmentResult(BaseModel):
    """
    Domain-level model for Step 8C train enrichment.
    Holds enriched data for all candidate trains discovered by Step 8B.
    """
    trains: list[TrainEnrichment] = Field(
        default_factory=list,
        description="List of enriched train entries"
    )
    status: Literal[
        "NOT_ENRICHED",
        "TRAINS_ENRICHED",
        "PARTIALLY_ENRICHED",
        "API_ERROR",
    ] = Field(
        default="NOT_ENRICHED",
        description="Overall status of train enrichment"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if enrichment provider failed"
    )


class RailTransportResult(BaseModel):
    """
    Unified domain-level result for the Rail subsystem containing all layers:
    1. Physical station discovery (OpenStreetMap/Overpass)
    2. Scheduled train connectivity (RailRadar)
    3. Train enrichment (Qrail details & running status)
    """
    station_discovery: RailStationDiscoveryResult = Field(
        ...,
        description="Physical railway station discovery result near source and destination"
    )
    train_connectivity: TrainConnectivityResult = Field(
        default_factory=TrainConnectivityResult,
        description="Scheduled train service connectivity between candidate stations"
    )
    train_enrichment: Optional[TrainEnrichmentResult] = Field(
        default=None,
        description="Optional train-specific enrichment details and running status"
    )

    # Convenience delegators for domain ergonomics and backwards compatibility
    @property
    def status(self) -> str:
        """Reflects train_connectivity status if checked, otherwise station_discovery status."""
        if self.train_connectivity.status != "NOT_CHECKED":
            return self.train_connectivity.status
        return self.station_discovery.status

    @property
    def source(self) -> str:
        return self.station_discovery.source

    @property
    def destination(self) -> str:
        return self.station_discovery.destination

    @property
    def source_stations(self) -> list[RailwayStation]:
        return self.station_discovery.source_stations

    @property
    def destination_stations(self) -> list[RailwayStation]:
        return self.station_discovery.destination_stations

    @property
    def trains(self) -> list[TrainService]:
        return self.train_connectivity.trains

    @property
    def error_message(self) -> Optional[str]:
        return self.train_connectivity.error_message or self.station_discovery.error_message


# Backwards compatibility alias
RailConnectivityResult = RailTransportResult


class TransportationResult(BaseModel):
    """
    Domain-level result for the entire transportation subsystem.
    Aggregates results across modalities (Road, Rail station discovery, train connectivity & enrichment).
    """
    road: Optional[RoadRouteResult] = Field(
        default=None,
        description="Road routing result between source and destination"
    )
    rail: Optional[RailTransportResult] = Field(
        default=None,
        description="Rail subsystem result combining physical station discovery, train connectivity, and enrichment"
    )

    @property
    def rail_station_discovery(self) -> Optional[RailStationDiscoveryResult]:
        """Explicit semantic accessor for rail physical station discovery result."""
        return self.rail.station_discovery if self.rail else None

    @property
    def train_connectivity(self) -> Optional[TrainConnectivityResult]:
        """Explicit semantic accessor for train service connectivity result."""
        return self.rail.train_connectivity if self.rail else None

    @property
    def train_enrichment(self) -> Optional[TrainEnrichmentResult]:
        """Explicit semantic accessor for train enrichment result."""
        return self.rail.train_enrichment if self.rail else None


class ModalOptionEvaluation(BaseModel):
    """
    Factual evaluation of a specific transportation modality.
    """
    modality: Literal["road", "rail"] = Field(
        ...,
        description="Transportation modality evaluated"
    )
    available: bool = Field(
        ...,
        description="Whether this modality is viable based on collected facts"
    )
    summary: str = Field(
        ...,
        description="Brief factual summary of availability, duration, distance, or failure reason"
    )
    duration_summary: Optional[str] = Field(
        default=None,
        description="Factual travel duration if known from facts, else None"
    )
    distance_km: Optional[float] = Field(
        default=None,
        description="Factual travel distance in km if known from facts, else None"
    )
    supported_services_or_routes: list[str] = Field(
        default_factory=list,
        description="Factual train numbers/names or route summary explicitly found in the data"
    )
    unsupported_or_missing_info: list[str] = Field(
        default_factory=list,
        description="Information missing from facts (e.g. 'Fares not available', 'Live running status unavailable')"
    )


class TransportationRecommendation(BaseModel):
    """
    LLM-generated interpretation and structured recommendation based ONLY on supplied TransportationResult facts.
    """
    status: Literal["RECOMMENDATION_MADE", "NO_VIABLE_OPTION", "DECISION_ERROR"] = Field(
        ...,
        description="Overall outcome of the transportation decision"
    )
    available_options: list[ModalOptionEvaluation] = Field(
        default_factory=list,
        description="Evaluations for each evaluated modality (road, rail)"
    )
    recommended_option: Optional[Literal["road", "rail", "both", "none"]] = Field(
        default=None,
        description="Recommended modality based on factual comparison, or 'none' if no options exist"
    )
    primary_recommendation_reason: str = Field(
        ...,
        description="Factual rationale for the recommendation (e.g. comparing duration, directness, or citing lack of options)"
    )
    limitations: list[str] = Field(
        default_factory=list,
        description="Explicit limitations and unknown data (e.g. ticket prices, seat availability, live delays)"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if decision agent encountered a processing or parsing failure"
    )


class TransportState(TypedDict):
    source: str
    destination: str
    date_of_travel: Optional[str]
    road_result: Optional[RoadRouteResult]
    rail_result: Optional[RailTransportResult]
    result: Optional[TransportationResult]






