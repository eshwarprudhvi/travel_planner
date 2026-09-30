"""
Unit and integration tests for Step 8C: Qrail Train Enrichment.

Tests:
1. Mocked Qrail Client with successful responses.
2. Mocked Qrail Client with HTTP 403 (Account disabled / contact support).
3. Mocked Qrail Client with HTTP 401 (Authentication failed).
4. Mocked Qrail Client with HTTP 404 (Train not found).
5. Per-train error isolation (Train A succeeds, Train B fails with 404, Train C fails with 403).
6. Multi-stage Rail Subgraph compilation and execution with Qrail enrichment node.
"""
import os
import sys

sys.path.insert(0, os.path.abspath("src"))

import pytest
from unittest.mock import MagicMock, patch

from travel_planner.transport.state import (
    RailwayStation,
    TrainService,
    RailStationDiscoveryResult,
    TrainConnectivityResult,
    TrainDetails,
    TrainRunningStatus,
    TrainEnrichment,
    TrainEnrichmentResult,
    RailTransportResult,
    TransportationResult,
)
from travel_planner.transport.services.qrail_client import (
    QrailClient,
    QrailApiError,
    QrailAccessDisabledError,
    QrailAuthenticationError,
)
from travel_planner.transport.tools.rail.enrichment_tool import (
    enrich_train_details,
    enrich_train_running_status,
    enrich_discovered_trains,
)
from travel_planner.transport.rail_graph import create_rail_graph, RailState


def test_qrail_client_success_mock():
    client = QrailClient(api_key="test_dummy_key")
    mock_details_payload = {
        "success": True,
        "data": {
            "train_number": "12393",
            "train_name": "SAMPOORNA KRANTI EXP",
        }
    }
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_details_payload
        mock_get.return_value = mock_resp

        res = client.get_train_details("12393")
        assert res == mock_details_payload
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert kwargs["params"] == {"train": "12393"}
        assert "Authorization" in kwargs["headers"]
        assert kwargs["headers"]["Authorization"] == "Bearer test_dummy_key"


def test_qrail_client_403_access_disabled():
    client = QrailClient(api_key="test_dummy_key")
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.json.return_value = {"error": "API access disabled, Please contact support."}
        mock_get.return_value = mock_resp

        with pytest.raises(QrailAccessDisabledError) as exc_info:
            client.get_train_details("12393")
        assert "API access disabled" in str(exc_info.value)
        # Verify key is never in exception string
        assert "test_dummy_key" not in str(exc_info.value)


def test_qrail_client_401_unauthorized():
    client = QrailClient(api_key="test_dummy_key")
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {"message": "Unauthenticated."}
        mock_get.return_value = mock_resp

        with pytest.raises(QrailAuthenticationError):
            client.get_train_running_status("12393")


def test_qrail_client_404_not_found():
    client = QrailClient(api_key="test_dummy_key")
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"success": False, "message": "Invalid Data!", "error": ""}
        mock_get.return_value = mock_resp

        res = client.get_train_details("99999")
        assert res is None


def test_enrich_discovered_trains_per_train_isolation():
    mock_client = MagicMock(spec=QrailClient)

    def fake_details(train_no):
        if train_no == "12393":
            return {"train_number": "12393", "train_name": "Sampoorna Kranti"}
        elif train_no == "00000":
            return None  # 404
        elif train_no == "12785":
            raise QrailAccessDisabledError("API access disabled")
        raise QrailApiError("General error")

    def fake_running(train_no):
        if train_no == "12393":
            return {"train_number": "12393", "current_station": "CNB", "delay": 5}
        elif train_no == "00000":
            return None
        elif train_no == "12785":
            raise QrailAccessDisabledError("API access disabled")
        raise QrailApiError("General error")

    mock_client.get_train_details.side_effect = fake_details
    mock_client.get_train_running_status.side_effect = fake_running

    train_numbers = ["12393", "00000", "12785", "12393"]  # includes duplicate
    result = enrich_discovered_trains(train_numbers, client=mock_client)

    assert isinstance(result, TrainEnrichmentResult)
    # Deduplicated: 3 unique trains
    assert len(result.trains) == 3

    # Train 12393: fully enriched
    t1 = result.trains[0]
    assert t1.train_number == "12393"
    assert t1.status == "ENRICHED"
    assert t1.details.status == "SUCCESS"
    assert t1.details.provisional_details["train_name"] == "Sampoorna Kranti"
    assert t1.running_status.status == "SUCCESS"
    assert t1.running_status.provisional_running_status["delay"] == 5

    # Train 00000: not found
    t2 = result.trains[1]
    assert t2.train_number == "00000"
    assert t2.status == "FAILED"
    assert t2.details.status == "NOT_FOUND"
    assert t2.running_status.status == "NOT_FOUND"

    # Train 12785: 403 API Error isolated
    t3 = result.trains[2]
    assert t3.train_number == "12785"
    assert t3.status == "FAILED"
    assert t3.details.status == "API_ERROR"
    assert "API access disabled" in t3.details.error_message
    assert t3.running_status.status == "API_ERROR"

    # Overall status should be PARTIALLY_ENRICHED because 12393 succeeded
    assert result.status == "PARTIALLY_ENRICHED"


def test_enrich_discovered_trains_all_403():
    mock_client = MagicMock(spec=QrailClient)
    mock_client.get_train_details.side_effect = QrailAccessDisabledError("API access disabled (HTTP 403)")
    mock_client.get_train_running_status.side_effect = QrailAccessDisabledError("API access disabled (HTTP 403)")

    result = enrich_discovered_trains(["12785", "12786"], client=mock_client)
    assert result.status == "API_ERROR"
    assert "API access disabled" in (result.error_message or "")
    assert len(result.trains) == 2
    assert result.trains[0].details.status == "API_ERROR"


def test_rail_subgraph_with_enrichment_flow():
    """Verify that the rail subgraph routes through train_enrichment and packages everything into RailTransportResult."""
    graph = create_rail_graph()

    # Pre-populate state as if stage 1, 2, and 3 ran
    state: RailState = {
        "source": "Hyderabad",
        "destination": "Bengaluru",
        "date_of_travel": None,
        "station_discovery": RailStationDiscoveryResult(
            source="Hyderabad",
            destination="Bengaluru",
            source_stations=[
                RailwayStation(
                    name="Secunderabad Junction",
                    latitude=17.43,
                    longitude=78.50,
                    railway_type="station",
                    distance_from_location_km=4.2,
                )
            ],
            destination_stations=[
                RailwayStation(
                    name="KSR Bengaluru City Junction",
                    latitude=12.97,
                    longitude=77.57,
                    railway_type="station",
                    distance_from_location_km=2.1,
                )
            ],
            status="STATIONS_FOUND",
        ),
        "source_station_codes": ["SC"],
        "destination_station_codes": ["SBC"],
        "train_connectivity": TrainConnectivityResult(
            source_station_code="SC",
            destination_station_code="SBC",
            trains=[
                TrainService(
                    train_number="12785",
                    train_name="Kacheguda - Mysuru SF Express",
                    source_station_code="KCG",
                    destination_station_code="SBC",
                )
            ],
            status="TRAINS_FOUND",
        ),
        "train_enrichment": None,
        "result": None,
    }

    # Mock station discovery, station code resolution, train connectivity, and Qrail client so network calls are isolated
    with patch("travel_planner.transport.rail_graph.find_nearby_railway_stations", return_value=state["station_discovery"]), \
         patch("travel_planner.transport.rail_graph.resolve_station_code", side_effect=lambda name: "SC" if "Secunderabad" in name else "SBC"), \
         patch("travel_planner.transport.rail_graph.discover_train_services", return_value=state["train_connectivity"]), \
         patch("travel_planner.transport.tools.rail.enrichment_tool.QrailClient") as mock_qrail_cls:
        instance = mock_qrail_cls.return_value
        instance.get_train_details.return_value = {"provisional": "data"}
        instance.get_train_running_status.return_value = {"provisional": "live_data"}

        output = graph.invoke(state)

        result: RailTransportResult = output["result"]
        assert result is not None
        assert result.station_discovery.status == "STATIONS_FOUND"
        assert result.train_connectivity.status == "TRAINS_FOUND"
        assert len(result.train_connectivity.trains) == 1
        assert result.train_enrichment is not None
        assert result.train_enrichment.status == "TRAINS_ENRICHED"
        assert result.train_enrichment.trains[0].train_number == "12785"
        assert result.train_enrichment.trains[0].details.provisional_details == {"provisional": "data"}


if __name__ == "__main__":
    pytest.main(["-v", __file__])
