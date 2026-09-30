"""
RailRadar API Client Boundary.
Encapsulates HTTP communication with https://api.railradar.in/v1 for:
1. Station autocomplete/lookup (/v1/lookup/search/stations)
2. Trains between stations (/v1/trains/between/{from}/{to})
"""
from typing import Any, Dict, List, Optional
import requests
from travel_planner.config.api_keys import RAILRADAR_API_KEY

BASE_URL = "https://api.railradar.in/v1"
STATION_SEARCH_URL = f"{BASE_URL}/lookup/search/stations"
TRAINS_BETWEEN_URL = f"{BASE_URL}/trains/between"


def get_auth_headers() -> Dict[str, str]:
    """
    Constructs authorization headers for RailRadar API requests.
    Raises ValueError if RAILRADAR_API_KEY is not configured.
    """
    if not RAILRADAR_API_KEY:
        raise ValueError(
            "RAILRADAR_API_KEY is not set in environment variables. "
            "Please add RAILRADAR_API_KEY to your .env file."
        )
    key = RAILRADAR_API_KEY.strip()
    return {
        "Authorization": f"Bearer {key}",
        "x-api-key": key,
        "Accept": "application/json",
        "User-Agent": "TravelPlanner/1.0",
    }


def search_stations(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Queries RailRadar's station autocomplete API to resolve station codes.
    GET /v1/lookup/search/stations?q={query}&limit={limit}
    
    Returns a list of station dictionaries from verified response:
    [
        {"code": "SC", "name": "Secunderabad Junction", "city": "Secunderabad"},
        ...
    ]
    """
    import sys
    headers = get_auth_headers()
    params = {"q": query.strip(), "limit": limit}

    try:
        response = requests.get(
            STATION_SEARCH_URL,
            headers=headers,
            params=params,
            timeout=10,
        )
        if response.status_code != 200:
            print(
                f"[DEBUG RailRadar] search_stations('{query}') status={response.status_code}, response={response.text[:200]}",
                file=sys.stderr,
            )
        if response.status_code in (401, 403):
            raise PermissionError(f"RailRadar authentication failed ({response.status_code}): {response.text[:100]}")
        if response.status_code == 429:
            raise RuntimeError("RailRadar rate limit exceeded (1,000 requests/month quota).")
        if response.status_code == 404:
            return []
        response.raise_for_status()


        data = response.json()
        raw_stations = data.get("data", [])
        if isinstance(raw_stations, list):
            return raw_stations[:limit]
        if isinstance(raw_stations, dict):
            stations = raw_stations.get("stations") or raw_stations.get("results") or []
            return stations[:limit]

        return []
    except requests.RequestException as err:
        raise RuntimeError(f"RailRadar station search network error: {err}") from err


def get_trains_between_stations(
    from_code: str,
    to_code: str,
    date: Optional[str] = None,
    timeout_seconds: int = 15,
) -> List[Dict[str, Any]]:
    """
    Retrieves scheduled trains operating between two railway station codes.
    GET /v1/trains/between/{from}/{to}?date=YYYY-MM-DD
    
    Parameters:
    - from_code: Origin railway station code (e.g. 'SC', 'NDLS')
    - to_code: Destination railway station code (e.g. 'SBC', 'MMCT')
    - date: Optional departure date at source in YYYY-MM-DD format
    - timeout_seconds: HTTP timeout in seconds

    Returns:
    - List of raw train service dictionaries extracted from data["trains"].
    """
    headers = get_auth_headers()
    clean_from = from_code.upper().strip()
    clean_to = to_code.upper().strip()
    endpoint = f"{TRAINS_BETWEEN_URL}/{clean_from}/{clean_to}"

    params = {}
    if date and date.strip():
        params["date"] = date.strip()

    try:
        response = requests.get(
            endpoint,
            headers=headers,
            params=params,
            timeout=timeout_seconds,
        )
        if response.status_code in (401, 403):
            raise PermissionError("RailRadar authentication failed. Please check your RAILRADAR_API_KEY.")
        if response.status_code == 429:
            raise RuntimeError("RailRadar rate limit exceeded (1,000 requests/month quota).")
        if response.status_code == 404:
            # 404 indicates no trains found between these stations
            return []
        response.raise_for_status()

        data = response.json()
        if not data.get("success", False) and "error" in data:
            error_info = data.get("error", {})
            error_msg = error_info.get("message", "Unknown RailRadar API error")
            raise RuntimeError(f"RailRadar API error: {error_msg}")

        train_data = data.get("data", {})
        if isinstance(train_data, dict):
            trains = train_data.get("trains", [])
        elif isinstance(train_data, list):
            trains = train_data
        else:
            trains = []

        return trains
    except requests.RequestException as err:
        raise RuntimeError(f"RailRadar trains-between network error: {err}") from err

