from langsmith import traceable
import requests
from travel_planner.transport.state import RoadRouteResult
from travel_planner.transport.services.openrouteservice_client import (
    geocode_place,
    request_driving_directions,
)


def _format_duration(seconds: float) -> str:
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    if hours > 0:
        return f"{hours} hours {minutes} mins"
    return f"{minutes} mins"


@traceable(run_type="tool", name="compute_road_route")
def compute_road_route(source: str, destination: str) -> RoadRouteResult:
    """
    Road routing tool boundary using OpenRouteService.
    
    1. Resolves source place to coordinates.
    2. Resolves destination place to coordinates.
    3. Requests driving directions between coordinates.
    4. Returns a standardized RoadRouteResult distinguishing route existence
       from resolution or API failures.
    """
    # 1. Geocode Source
    try:
        start_coords = geocode_place(source)
    except Exception as e:
        return RoadRouteResult(
            available=False,
            source=source,
            destination=destination,
            status="API_ERROR",
            error_message=f"Geocoding API error resolving source: {str(e)}",
        )

    if not start_coords:
        return RoadRouteResult(
            available=False,
            source=source,
            destination=destination,
            status="SOURCE_UNRESOLVABLE",
            error_message=f"Could not resolve location for source: '{source}'",
        )

    # 2. Geocode Destination
    try:
        end_coords = geocode_place(destination)
    except Exception as e:
        return RoadRouteResult(
            available=False,
            source=source,
            destination=destination,
            status="API_ERROR",
            error_message=f"Geocoding API error resolving destination: {str(e)}",
        )

    if not end_coords:
        return RoadRouteResult(
            available=False,
            source=source,
            destination=destination,
            status="DESTINATION_UNRESOLVABLE",
            error_message=f"Could not resolve location for destination: '{destination}'",
        )

    # 3. Request Driving Directions
    try:
        response_data = request_driving_directions(start_coords, end_coords)
    except requests.exceptions.HTTPError as http_err:
        status_code = http_err.response.status_code if http_err.response is not None else None
        if status_code in (404, 400):
            return RoadRouteResult(
                available=False,
                source=source,
                destination=destination,
                status="NO_ROUTE_EXISTS",
                error_message=f"No driving route found between '{source}' and '{destination}'",
            )
        return RoadRouteResult(
            available=False,
            source=source,
            destination=destination,
            status="API_ERROR",
            error_message=f"OpenRouteService API HTTP error: {str(http_err)}",
        )
    except Exception as e:
        return RoadRouteResult(
            available=False,
            source=source,
            destination=destination,
            status="API_ERROR",
            error_message=f"OpenRouteService directions error: {str(e)}",
        )

    # 4. Parse Route Results
    routes = response_data.get("routes", [])
    if not routes:
        return RoadRouteResult(
            available=False,
            source=source,
            destination=destination,
            status="NO_ROUTE_EXISTS",
            error_message=f"No driving route exists between '{source}' and '{destination}'",
        )

    primary_route = routes[0]
    summary = primary_route.get("summary", {})
    distance_meters = summary.get("distance", 0.0)
    duration_seconds = summary.get("duration", 0.0)

    distance_km = round(distance_meters / 1000.0, 1)
    duration_formatted = _format_duration(duration_seconds)

    return RoadRouteResult(
        available=True,
        source=source,
        destination=destination,
        distance_km=distance_km,
        duration_seconds=int(duration_seconds),
        duration_formatted=duration_formatted,
        status="ROUTE_FOUND",
    )
