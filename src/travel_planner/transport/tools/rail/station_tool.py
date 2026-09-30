"""
Railway Station Discovery Tool.
Finds candidate railway stations near source and destination locations
using geographic coordinates and OpenStreetMap Overpass API data.
"""
import math
from typing import List, Optional
from travel_planner.transport.services.openrouteservice_client import geocode_place
from travel_planner.transport.services.railway_station_client import query_nearby_railway_stations
from travel_planner.transport.state import RailwayStation, RailStationDiscoveryResult


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes great-circle distance between two (lat, lon) points in kilometers.
    """
    earth_radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(earth_radius_km * c, 2)


def _process_station_candidates(
    raw_stations: List[dict],
    origin_lat: float,
    origin_lon: float,
    limit: int = 5,
) -> List[RailwayStation]:
    """
    Calculates distances, deduplicates multiple OSM elements for the same station,
    and returns the top candidates sorted by proximity.
    """
    stations_by_name: dict[str, RailwayStation] = {}

    for raw in raw_stations:
        dist = haversine_distance_km(
            origin_lat, origin_lon, raw["latitude"], raw["longitude"]
        )
        station = RailwayStation(
            name=raw["name"],
            latitude=raw["latitude"],
            longitude=raw["longitude"],
            railway_type=raw["railway_type"],
            distance_from_location_km=dist,
        )

        norm_name = raw["name"].strip().lower()
        if norm_name not in stations_by_name or dist < stations_by_name[norm_name].distance_from_location_km:
            stations_by_name[norm_name] = station

    sorted_stations = sorted(
        stations_by_name.values(),
        key=lambda s: s.distance_from_location_km
    )
    return sorted_stations[:limit]


def find_nearby_railway_stations(
    source: str,
    destination: str,
    radius_km: float = 50.0,
    limit: int = 5,
) -> RailStationDiscoveryResult:
    """
    Given a source and destination, resolves coordinates and searches for candidate
    passenger railway stations within `radius_km` of both locations.

    Parameters:
    - source: Origin place name (e.g. "Hyderabad", "Madhapur")
    - destination: Destination place name (e.g. "Bengaluru")
    - radius_km: Search radius in kilometers (default: 50.0 km)
    - limit: Maximum number of closest candidate stations to return per endpoint (default: 5)

    Returns:
    - RailStationDiscoveryResult containing candidate stations and discovery status.
    """
    # 1. Resolve source coordinates
    try:
        source_coords = geocode_place(source)
    except Exception as err:
        return RailStationDiscoveryResult(
            source=source,
            destination=destination,
            source_stations=[],
            destination_stations=[],
            status="API_ERROR",
            error_message=f"Failed to geocode source '{source}': {err}",
        )

    if not source_coords:
        return RailStationDiscoveryResult(
            source=source,
            destination=destination,
            source_stations=[],
            destination_stations=[],
            status="API_ERROR",
            error_message=f"Source location '{source}' could not be resolved to coordinates",
        )

    # 2. Resolve destination coordinates
    try:
        dest_coords = geocode_place(destination)
    except Exception as err:
        return RailStationDiscoveryResult(
            source=source,
            destination=destination,
            source_stations=[],
            destination_stations=[],
            status="API_ERROR",
            error_message=f"Failed to geocode destination '{destination}': {err}",
        )

    if not dest_coords:
        return RailStationDiscoveryResult(
            source=source,
            destination=destination,
            source_stations=[],
            destination_stations=[],
            status="API_ERROR",
            error_message=f"Destination location '{destination}' could not be resolved to coordinates",
        )

    # GeoJSON coordinates format is [longitude, latitude]
    source_lon, source_lat = source_coords[0], source_coords[1]
    dest_lon, dest_lat = dest_coords[0], dest_coords[1]
    radius_meters = int(radius_km * 1000)

    # 3. Query stations near source
    try:
        raw_source_stations = query_nearby_railway_stations(
            latitude=source_lat,
            longitude=source_lon,
            radius_meters=radius_meters,
        )
        source_candidates = _process_station_candidates(
            raw_source_stations, source_lat, source_lon, limit=limit
        )
    except Exception as err:
        return RailStationDiscoveryResult(
            source=source,
            destination=destination,
            source_stations=[],
            destination_stations=[],
            status="API_ERROR",
            error_message=f"Failed to query railway stations near source '{source}': {err}",
        )

    # 4. Query stations near destination
    try:
        raw_dest_stations = query_nearby_railway_stations(
            latitude=dest_lat,
            longitude=dest_lon,
            radius_meters=radius_meters,
        )
        dest_candidates = _process_station_candidates(
            raw_dest_stations, dest_lat, dest_lon, limit=limit
        )
    except Exception as err:
        return RailStationDiscoveryResult(
            source=source,
            destination=destination,
            source_stations=source_candidates,
            destination_stations=[],
            status="API_ERROR",
            error_message=f"Failed to query railway stations near destination '{destination}': {err}",
        )

    # 5. Determine domain status
    has_source = len(source_candidates) > 0
    has_dest = len(dest_candidates) > 0

    if has_source and has_dest:
        status = "STATIONS_FOUND"
    elif not has_source and not has_dest:
        status = "NO_STATIONS_FOUND"
    elif not has_source:
        status = "NO_SOURCE_STATION"
    else:
        status = "NO_DESTINATION_STATION"

    return RailStationDiscoveryResult(
        source=source,
        destination=destination,
        source_stations=source_candidates,
        destination_stations=dest_candidates,
        status=status,
    )

