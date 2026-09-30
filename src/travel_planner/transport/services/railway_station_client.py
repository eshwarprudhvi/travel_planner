"""
OpenStreetMap / Overpass API Client for Railway Station queries.
Queries candidate passenger railway stations ('station' and 'halt') within a radius around coordinates.
"""
from typing import Any, Dict, List, Optional
import requests

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

USER_AGENT = "TravelPlannerAgent/1.0 (educational-agentic-workflow)"



def query_nearby_railway_stations(
    latitude: float,
    longitude: float,
    radius_meters: int = 50000,
    timeout_seconds: int = 25,
) -> List[Dict[str, Any]]:
    """
    Queries OpenStreetMap via Overpass API for railway stations ('station' or 'halt')
    within `radius_meters` around (latitude, longitude).

    Returns a list of dictionaries with raw station info:
    [
        {
            "name": str,
            "latitude": float,
            "longitude": float,
            "railway_type": str,  # 'station' or 'halt'
        },
        ...
    ]
    """
    overpass_query = f"""[out:json][timeout:{timeout_seconds}];
(
  nwr["railway"="station"](around:{radius_meters},{latitude},{longitude});
  nwr["railway"="halt"](around:{radius_meters},{latitude},{longitude});
);
out center tags;
"""

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }

    last_error: Optional[Exception] = None

    for endpoint in OVERPASS_ENDPOINTS:
        try:
            response = requests.post(
                endpoint,
                data={"data": overpass_query},
                headers=headers,
                timeout=timeout_seconds + 5,
            )
            response.raise_for_status()
            data = response.json()
            elements = data.get("elements", [])
            stations = []

            for element in elements:
                tags = element.get("tags", {})
                railway_type = tags.get("railway")
                if railway_type not in ("station", "halt"):
                    continue

                # Exclude abandoned or disused stations
                if tags.get("abandoned") == "yes" or tags.get("disused") == "yes":
                    continue

                # Exclude urban subway / metro stations and light rail / bus
                name = tags.get("name") or tags.get("name:en")
                if not name:
                    continue

                lower_name = name.lower()
                network = (tags.get("network") or "").lower()
                operator = (tags.get("operator") or "").lower()

                if (
                    tags.get("station") == "subway"
                    or tags.get("subway") == "yes"
                    or tags.get("light_rail") == "yes"
                    or "metro" in network
                    or "metro" in operator
                    or "metro" in lower_name
                    or "bus station" in lower_name
                    or "line)" in lower_name
                ):
                    continue

                # Resolve coordinates

                if element.get("type") == "node":
                    lat = element.get("lat")
                    lon = element.get("lon")
                else:
                    center = element.get("center", {})
                    lat = center.get("lat")
                    lon = center.get("lon")

                if lat is None or lon is None:
                    continue

                stations.append({
                    "name": name.strip(),
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "railway_type": railway_type,
                })

            return stations

        except (requests.RequestException, ValueError) as err:
            last_error = err
            continue

    # If all endpoints failed
    raise RuntimeError(
        f"Failed to query railway stations from Overpass API: {last_error}"
    )
