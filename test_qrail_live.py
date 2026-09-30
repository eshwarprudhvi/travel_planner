"""
Test authentication header styles for api.qrail.in.
"""
import os
import sys
import requests

sys.path.insert(0, os.path.abspath("src"))
from travel_planner.config.api_keys import QRAIL_API_KEY

BASE_URL = "https://api.qrail.in"
URL = f"{BASE_URL}/api/v1/trains/details"
key = QRAIL_API_KEY.strip()

tests = [
    ("Bearer", {"Authorization": f"Bearer {key}"}, {"train": "12393"}),
    ("Token", {"Authorization": f"Token {key}"}, {"train": "12393"}),
    ("Raw Auth", {"Authorization": key}, {"train": "12393"}),
    ("x-api-key", {"x-api-key": key}, {"train": "12393"}),
    ("X-API-KEY", {"X-API-KEY": key}, {"train": "12393"}),
    ("apikey header", {"apikey": key}, {"train": "12393"}),
    ("query apikey", {}, {"train": "12393", "apikey": key}),
    ("query api_key", {}, {"train": "12393", "api_key": key}),
    ("query key", {}, {"train": "12393", "key": key}),
]

for label, headers, params in tests:
    headers["Accept"] = "application/json"
    headers["User-Agent"] = "TravelPlanner/1.0"
    try:
        r = requests.get(URL, headers=headers, params=params, timeout=10)
        print(f"[{label}] Status: {r.status_code} -> Resp: {r.text[:150]}")
    except Exception as e:
        print(f"[{label}] Error: {e}")
