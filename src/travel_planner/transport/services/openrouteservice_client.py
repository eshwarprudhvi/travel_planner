"""
OpenRouteService API Client Boundary.
Uses the current HeiGIT unified infrastructure (api.heigit.org).
Handles HTTP communication for Pelias geocoding and v2 driving directions.
"""
from typing import Any, Dict, List, Optional
import requests
from travel_planner.config.api_keys import OPENROUTESERVICE_API_KEY

BASE_URL = "https://api.heigit.org"
GEOCODE_SEARCH_URL = f"{BASE_URL}/pelias/v1/search"
DIRECTIONS_DRIVING_URL = f"{BASE_URL}/openrouteservice/v2/directions/driving-car"


def get_auth_headers() -> Dict[str, str]:
    """
    Constructs authorization headers for OpenRouteService requests.
    """
    if not OPENROUTESERVICE_API_KEY:
        raise ValueError(
            "OPENROUTESERVICE_API_KEY is not set. Please set it in your .env file."
        )
    return {
        "Authorization": OPENROUTESERVICE_API_KEY,
        "Accept": "application/json, application/geo+json",
        "Content-Type": "application/json; charset=utf-8",
    }


def geocode_place(place_name: str) -> Optional[List[float]]:
    """
    Resolves a place name into [longitude, latitude] coordinates
    using the Pelias geocoding API.
    
    Returns:
    - [longitude, latitude] if resolved, or None if no match found.
    """
    headers = get_auth_headers()
    params = {"text": place_name, "size": 1}

    response = requests.get(GEOCODE_SEARCH_URL, headers=headers, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()
    features = data.get("features", [])
    if not features:
        return None

    # GeoJSON coordinates format is [longitude, latitude]
    geometry = features[0].get("geometry", {})
    coordinates = geometry.get("coordinates")
    return coordinates


def request_driving_directions(
    start_coords: List[float],
    end_coords: List[float]
) -> Dict[str, Any]:
    """
    Requests driving directions between two [lng, lat] points
    using the OpenRouteService v2 directions endpoint.

    Parameters:
    - start_coords: [start_longitude, start_latitude]
    - end_coords: [end_longitude, end_latitude]

    Returns:
    - Raw API JSON response dictionary.
    """
    headers = get_auth_headers()
    payload = {
        "coordinates": [start_coords, end_coords],
    }

    response = requests.post(DIRECTIONS_DRIVING_URL, headers=headers, json=payload, timeout=15)
    response.raise_for_status()
    return response.json()
