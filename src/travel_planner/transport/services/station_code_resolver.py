"""
Railway Station Code Resolver Service.
Resolves physical OpenStreetMap railway station names into Indian Railways
station codes (e.g. 'Secunderabad' -> 'SC', 'KSR Bengaluru' -> 'SBC').
"""
import re
from typing import Optional
from travel_planner.transport.services.railradar_client import search_stations


def clean_station_name(name: str) -> str:
    """
    Strips noise words and parenthetical aliases commonly attached in OSM labels
    (e.g. 'KSR Bengaluru (Bangalore)', 'Secunderabad Junction') to improve match
    accuracy against Indian Railways station databases.
    """
    # Remove parenthetical details like (Bangalore), (HWH), etc.
    cleaned = re.sub(r"\(.*?\)", "", name)
    # Remove common railway station noise words
    cleaned = re.sub(
        r"\b(railway station|railway|station|junction|jct|terminal|cantt|cantonment|city|central|halt)\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return " ".join(cleaned.split()).strip()


_STATION_CODE_CACHE: dict[str, Optional[str]] = {}


def resolve_station_code(station_name: str) -> Optional[str]:
    """
    Resolves a physical railway station name to its official 2-5 letter station code.

    Strategy:
    1. If the input is already a 2-5 letter uppercase station code (e.g. 'SC', 'SBC'), return it.
    2. Check in-memory cache to conserve API quota.
    3. Query RailRadar's station autocomplete search API with the cleaned station name.
    4. If no match, try querying with the raw station name.
    5. Extract the station code from the top matching result.
    6. Return uppercase station code or None if unresolvable.
    """
    if not station_name or not station_name.strip():
        return None

    # If the string is already a 2-5 letter uppercase station code (e.g. 'SC', 'SBC', 'NDLS')
    trimmed = station_name.strip().upper()
    if re.fullmatch(r"[A-Z]{2,5}", trimmed):
        return trimmed

    cache_key = station_name.strip().lower()
    if cache_key in _STATION_CODE_CACHE:
        return _STATION_CODE_CACHE[cache_key]

    cleaned = clean_station_name(station_name)
    candidates_to_try = [cleaned, station_name.strip()] if cleaned and cleaned.lower() != station_name.lower().strip() else [station_name.strip()]

    for query_candidate in candidates_to_try:
        if not query_candidate:
            continue
        try:
            results = search_stations(query_candidate, limit=5)
            for res in results:
                code = res.get("code") or res.get("stationCode") or res.get("station_code")
                if code and re.fullmatch(r"[A-Za-z]{2,5}", str(code).strip()):
                    resolved = str(code).upper().strip()
                    _STATION_CODE_CACHE[cache_key] = resolved
                    return resolved
        except RuntimeError as rerr:
            if "rate limit" in str(rerr).lower():
                raise
        except Exception as err:
            import sys
            print(f"[DEBUG station_code_resolver] query '{query_candidate}' failed: {err}", file=sys.stderr)
            continue

    _STATION_CODE_CACHE[cache_key] = None
    return None



