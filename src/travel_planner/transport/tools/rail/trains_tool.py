"""
Train Connectivity Orchestration Tool.
Orchestrates:
1. Physical station discovery (OpenStreetMap/Overpass)
2. Station code resolution (OSM Names -> IR Codes via RailRadar search)
3. Station pair generation (Candidate Source x Destination bounded matrix)
4. Train discovery via RailRadar (GET /v1/trains/between/{from}/{to})
5. Normalization into TrainService domain models
6. Train deduplication by train_number
7. Production of TrainConnectivityResult and unified RailTransportResult
"""
import re
from typing import Dict, List, Optional
from travel_planner.transport.tools.rail.station_tool import find_nearby_railway_stations
from travel_planner.transport.services.station_code_resolver import resolve_station_code
from travel_planner.transport.services.railradar_client import get_trains_between_stations
from travel_planner.transport.state import (
    TrainService,
    RailStationDiscoveryResult,
    TrainConnectivityResult,
    RailTransportResult,
)


def _parse_duration_minutes(raw_duration: Optional[object]) -> Optional[int]:
    """
    Parses duration strings like '11h 45m', '11:45', or integer minutes into total minutes.
    """
    if raw_duration is None:
        return None
    if isinstance(raw_duration, (int, float)):
        return int(raw_duration)

    raw_str = str(raw_duration).strip()
    if raw_str.isdigit():
        return int(raw_str)

    # Match '11h 30m' or '11h30m'
    match_hm = re.match(r"(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?", raw_str, re.IGNORECASE)
    if match_hm and (match_hm.group(1) or match_hm.group(2)):
        hours = int(match_hm.group(1) or 0)
        minutes = int(match_hm.group(2) or 0)
        return hours * 60 + minutes

    # Match 'HH:MM'
    if ":" in raw_str:
        parts = raw_str.split(":")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            return int(parts[0]) * 60 + int(parts[1])

    return None


def _normalize_train(raw: dict, default_src: str, default_dst: str) -> TrainService:
    """
    Normalizes a raw train dictionary from RailRadar into a TrainService domain model.
    RailRadar verified structure:
    {
      "train": {"number": "69211", "name": "...", "type": "...", "runDays": [...]},
      "from": {"departure": "06:00", ...},
      "to": {"arrival": "07:55", ...},
      "distance": 62.2,
      "duration": 115
    }
    """
    train_obj = raw.get("train") if isinstance(raw.get("train"), dict) else {}
    from_obj = raw.get("from") if isinstance(raw.get("from"), dict) else {}
    to_obj = raw.get("to") if isinstance(raw.get("to"), dict) else {}

    train_number = str(
        train_obj.get("number")
        or raw.get("number")
        or raw.get("trainNumber")
        or raw.get("train_number")
        or "UNKNOWN"
    ).strip()

    train_name = str(
        train_obj.get("name")
        or raw.get("name")
        or raw.get("trainName")
        or raw.get("train_name")
        or f"Train {train_number}"
    ).strip()

    train_type = train_obj.get("type") or raw.get("type") or raw.get("trainType") or raw.get("category")

    src_code = str(
        from_obj.get("code")
        or raw.get("from")
        or raw.get("source")
        or default_src
    ).upper().strip()

    dst_code = str(
        to_obj.get("code")
        or raw.get("to")
        or raw.get("destination")
        or default_dst
    ).upper().strip()

    departure = from_obj.get("departure") or raw.get("departure") or raw.get("departureTime") or raw.get("dep")
    arrival = to_obj.get("arrival") or raw.get("arrival") or raw.get("arrivalTime") or raw.get("arr")

    duration = _parse_duration_minutes(raw.get("duration") or raw.get("travelTime"))

    dist_raw = raw.get("distance") or raw.get("distanceKm")
    try:
        distance_km = float(dist_raw) if dist_raw is not None else None
    except (ValueError, TypeError):
        distance_km = None

    raw_run_days = train_obj.get("runDays") or raw.get("days") or raw.get("runDays") or raw.get("runningDays")
    if isinstance(raw_run_days, list):
        run_days = [str(d).capitalize() for d in raw_run_days]
    elif isinstance(raw_run_days, str):
        run_days = [d.strip().capitalize() for d in raw_run_days.split(",") if d.strip()]
    else:
        run_days = None

    return TrainService(
        train_number=train_number,
        train_name=train_name,
        train_type=train_type,
        source_station_code=src_code,
        destination_station_code=dst_code,
        source_station_name=from_obj.get("name") or raw.get("sourceName") or raw.get("fromName"),
        destination_station_name=to_obj.get("name") or raw.get("destinationName") or raw.get("toName"),
        departure_time=str(departure) if departure else None,
        arrival_time=str(arrival) if arrival else None,
        duration_minutes=duration,
        distance_km=distance_km,
        run_days=run_days,
    )


def discover_train_services(
    source_codes: List[str],
    dest_codes: List[str],
    date_of_travel: Optional[str] = None,
    max_source_stations: int = 3,
    max_destination_stations: int = 3,
) -> TrainConnectivityResult:
    """
    Given resolved source and destination station codes, queries the train discovery
    API across candidate pairs and deduplicates results by train_number.

    Parameters:
    - source_codes: List of resolved origin station codes
    - dest_codes: List of resolved destination station codes
    - date_of_travel: Optional travel date (only passed if normalized YYYY-MM-DD)
    - max_source_stations: Limit for source candidates
    - max_destination_stations: Limit for destination candidates

    Returns:
    - TrainConnectivityResult with status TRAINS_FOUND, NO_TRAINS_FOUND,
      STATION_CODE_UNRESOLVABLE, or API_ERROR.
    """
    if not source_codes or not dest_codes:
        missing_side = "source" if not source_codes else "destination"
        return TrainConnectivityResult(
            source_station_code=source_codes[0] if source_codes else None,
            destination_station_code=dest_codes[0] if dest_codes else None,
            trains=[],
            status="STATION_CODE_UNRESOLVABLE",
            error_message=f"Could not resolve official railway station codes for {missing_side} candidate stations",
        )

    # Validate date: only pass to provider if already in normalized YYYY-MM-DD format
    normalized_date: Optional[str] = None
    if date_of_travel and re.fullmatch(r"^\d{4}-\d{2}-\d{2}$", date_of_travel.strip()):
        normalized_date = date_of_travel.strip()

    candidate_sources = source_codes[:max_source_stations]
    candidate_dests = dest_codes[:max_destination_stations]

    deduped_trains: Dict[str, TrainService] = {}
    api_errors: List[str] = []
    total_queries = 0

    for src_code in candidate_sources:
        for dst_code in candidate_dests:
            total_queries += 1
            try:
                raw_trains = get_trains_between_stations(
                    from_code=src_code,
                    to_code=dst_code,
                    date=normalized_date,
                )
                for raw in raw_trains:
                    train = _normalize_train(raw, default_src=src_code, default_dst=dst_code)
                    if train.train_number not in deduped_trains:
                        deduped_trains[train.train_number] = train
            except Exception as err:
                api_errors.append(f"Pair ({src_code} -> {dst_code}): {err}")

    # If any queries encountered API errors and no trains were returned
    if api_errors and not deduped_trains:
        return TrainConnectivityResult(
            source_station_code=candidate_sources[0] if candidate_sources else None,
            destination_station_code=candidate_dests[0] if candidate_dests else None,
            trains=[],
            status="API_ERROR",
            error_message="; ".join(api_errors[:2]),
        )


    trains_list = list(deduped_trains.values())
    status = "TRAINS_FOUND" if trains_list else "NO_TRAINS_FOUND"

    return TrainConnectivityResult(
        source_station_code=candidate_sources[0],
        destination_station_code=candidate_dests[0],
        trains=trains_list,
        status=status,
    )


def find_train_connections(
    source: str,
    destination: str,
    date_of_travel: Optional[str] = None,
    max_source_stations: int = 3,
    max_destination_stations: int = 3,
) -> RailTransportResult:
    """
    End-to-end orchestration for the Rail transportation subsystem.
    Executes:
    1. Spatial station discovery (find physical railway stations near both places)
    2. Resolve station codes for top candidate stations
    3. Train discovery API queries across candidate station pairs
    4. Deduplicate trains by train_number
    5. Returns unified RailTransportResult(station_discovery=..., train_connectivity=...)
    """
    # 1. Discover physical stations near source and destination
    spatial_result = find_nearby_railway_stations(
        source=source,
        destination=destination,
        radius_km=50.0,
        limit=10,
    )

    # If physical station discovery failed or found no stations at either endpoint
    if spatial_result.status in (
        "NO_SOURCE_STATION",
        "NO_DESTINATION_STATION",
        "NO_STATIONS_FOUND",
        "API_ERROR",
    ):
        return RailTransportResult(
            station_discovery=spatial_result,
            train_connectivity=TrainConnectivityResult(
                status="NOT_CHECKED",
                error_message=f"Train connectivity skipped due to station discovery status: {spatial_result.status}",
            ),
        )

    # 2. Resolve station codes for candidate stations, collecting up to max limits
    source_codes: List[str] = []
    dest_codes: List[str] = []
    try:
        for station in spatial_result.source_stations:
            code = resolve_station_code(station.name)
            if code and code not in source_codes:
                source_codes.append(code)
                if len(source_codes) >= max_source_stations:
                    break

        for station in spatial_result.destination_stations:
            code = resolve_station_code(station.name)
            if code and code not in dest_codes:
                dest_codes.append(code)
                if len(dest_codes) >= max_destination_stations:
                    break
    except Exception as err:
        return RailTransportResult(
            station_discovery=spatial_result,
            train_connectivity=TrainConnectivityResult(
                status="API_ERROR",
                error_message=f"Station code resolution API error: {err}",
            ),
        )

    # 3. Discover train services between resolved station codes
    train_connectivity = discover_train_services(
        source_codes=source_codes,
        dest_codes=dest_codes,
        date_of_travel=date_of_travel,
        max_source_stations=max_source_stations,
        max_destination_stations=max_destination_stations,
    )


    return RailTransportResult(
        station_discovery=spatial_result,
        train_connectivity=train_connectivity,
    )
