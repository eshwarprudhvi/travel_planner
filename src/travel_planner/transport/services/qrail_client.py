"""
Qrail API Client for train enrichment (details and live running status).

Verified Endpoint Contract:
GET https://api.qrail.in/api/v1/trains/details?train={train_number}
GET https://api.qrail.in/api/v1/trains/running-status?train={train_number}

Headers:
Authorization: Bearer <QRAIL_API_KEY>
Accept: application/json
User-Agent: TravelPlanner/1.0

Security & Safety:
- Never prints or logs the raw API key.
- Treats Qrail success schemas as provisional/unverified.
- Maps HTTP 403 to custom QrailAccessDisabledError / PermissionError.
"""
from typing import Any, Optional
import requests
from langsmith import traceable

from travel_planner.config.api_keys import QRAIL_API_KEY


class QrailApiError(Exception):
    """Base exception for Qrail API errors."""
    pass


class QrailAccessDisabledError(QrailApiError):
    """Raised when Qrail returns HTTP 403 (Account disabled / Contact support)."""
    pass


class QrailAuthenticationError(QrailApiError):
    """Raised when Qrail returns HTTP 401 (Unauthorized)."""
    pass


class QrailClient:
    """Client for querying Qrail enrichment endpoints."""

    BASE_URL = "https://api.qrail.in"

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = (api_key or QRAIL_API_KEY or "").strip()

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "TravelPlanner/1.0",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _request(self, endpoint: str, train_number: str) -> Optional[dict[str, Any]]:
        """
        Executes a GET request to Qrail with the given endpoint and train parameter.
        Handles status codes gracefully without exposing the API key.
        """
        if not self._api_key:
            raise QrailAuthenticationError("QRAIL_API_KEY is not set or empty.")

        url = f"{self.BASE_URL}{endpoint}"
        params = {"train": str(train_number).strip()}

        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=12,
            )
        except requests.RequestException as e:
            raise QrailApiError(f"Network error querying Qrail: {type(e).__name__}") from e

        if response.status_code == 200:
            try:
                data = response.json()
                return data
            except ValueError:
                raise QrailApiError("Qrail returned invalid JSON response on HTTP 200.")

        if response.status_code == 403:
            # Verified response: {"error": "API access disabled, Please contact support."}
            err_msg = "Qrail API access disabled: Please contact support (HTTP 403)"
            try:
                body = response.json()
                if isinstance(body, dict) and "error" in body:
                    err_msg = f"Qrail API access disabled (HTTP 403): {body['error']}"
            except Exception:
                pass
            raise QrailAccessDisabledError(err_msg)

        if response.status_code == 401:
            raise QrailAuthenticationError("Qrail authentication failed (HTTP 401).")

        if response.status_code == 404:
            # Train not found or invalid train number
            return None

        # Other HTTP errors (e.g. 500, 502, 429)
        raise QrailApiError(f"Qrail returned unexpected HTTP {response.status_code}.")

    @traceable(run_type="tool", name="qrail_get_train_details")
    def get_train_details(self, train_number: str) -> Optional[dict[str, Any]]:
        """
        Fetches train details/schedule for a given train number.
        Returns dict if found, None if train is not found, raises QrailApiError on provider errors.
        """
        return self._request("/api/v1/trains/details", train_number)

    @traceable(run_type="tool", name="qrail_get_train_running_status")
    def get_train_running_status(self, train_number: str) -> Optional[dict[str, Any]]:
        """
        Fetches live running status for a given train number.
        Returns dict if found, None if train is not found, raises QrailApiError on provider errors.
        """
        return self._request("/api/v1/trains/running-status", train_number)
