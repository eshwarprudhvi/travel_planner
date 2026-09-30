"""
Train enrichment tool for Step 8C.

Enriches discovered train services with details and running status using Qrail.
Maintains strict error isolation per-train and treats Qrail success payloads
as provisional/unverified without assuming speculative fields.
"""
from typing import Optional
from langsmith import traceable

from travel_planner.transport.state import (
    TrainDetails,
    TrainRunningStatus,
    TrainEnrichment,
    TrainEnrichmentResult,
)
from travel_planner.transport.services.qrail_client import (
    QrailClient,
    QrailApiError,
    QrailAccessDisabledError,
    QrailAuthenticationError,
)


@traceable(run_type="tool", name="enrich_train_details")
def enrich_train_details(
    train_number: str,
    client: Optional[QrailClient] = None,
) -> TrainDetails:
    """Fetches details for a single train number from Qrail with error isolation."""
    c = client or QrailClient()
    try:
        data = c.get_train_details(train_number)
        if data is None:
            return TrainDetails(
                train_number=train_number,
                status="NOT_FOUND",
                error_message="Train details not found on Qrail",
            )
        return TrainDetails(
            train_number=train_number,
            status="SUCCESS",
            provisional_details=data,
        )
    except QrailAccessDisabledError as e:
        return TrainDetails(
            train_number=train_number,
            status="API_ERROR",
            error_message=str(e),
        )
    except QrailAuthenticationError as e:
        return TrainDetails(
            train_number=train_number,
            status="API_ERROR",
            error_message=str(e),
        )
    except QrailApiError as e:
        return TrainDetails(
            train_number=train_number,
            status="API_ERROR",
            error_message=str(e),
        )
    except Exception as e:
        return TrainDetails(
            train_number=train_number,
            status="API_ERROR",
            error_message=f"Unexpected enrichment error: {type(e).__name__}",
        )


@traceable(run_type="tool", name="enrich_train_running_status")
def enrich_train_running_status(
    train_number: str,
    client: Optional[QrailClient] = None,
) -> TrainRunningStatus:
    """Fetches live running status for a single train number from Qrail with error isolation."""
    c = client or QrailClient()
    try:
        data = c.get_train_running_status(train_number)
        if data is None:
            return TrainRunningStatus(
                train_number=train_number,
                status="NOT_FOUND",
                error_message="Train running status not found on Qrail",
            )
        return TrainRunningStatus(
            train_number=train_number,
            status="SUCCESS",
            provisional_running_status=data,
        )
    except QrailAccessDisabledError as e:
        return TrainRunningStatus(
            train_number=train_number,
            status="API_ERROR",
            error_message=str(e),
        )
    except QrailAuthenticationError as e:
        return TrainRunningStatus(
            train_number=train_number,
            status="API_ERROR",
            error_message=str(e),
        )
    except QrailApiError as e:
        return TrainRunningStatus(
            train_number=train_number,
            status="API_ERROR",
            error_message=str(e),
        )
    except Exception as e:
        return TrainRunningStatus(
            train_number=train_number,
            status="API_ERROR",
            error_message=f"Unexpected enrichment error: {type(e).__name__}",
        )


@traceable(run_type="tool", name="enrich_discovered_trains")
def enrich_discovered_trains(
    train_numbers: list[str],
    client: Optional[QrailClient] = None,
) -> TrainEnrichmentResult:
    """
    Enriches a list of discovered train numbers with details and live running status.
    Guarantees that:
    1. Duplicate train numbers are deduplicated while preserving order.
    2. Failure of one train never blocks or affects other trains.
    3. If no trains are provided, returns NOT_ENRICHED status cleanly.
    4. Categorizes overall status:
       - NOT_ENRICHED if empty list.
       - TRAINS_ENRICHED if at least one train was successfully enriched.
       - PARTIALLY_ENRICHED if some succeeded and some failed.
       - API_ERROR if provider failed across the board.
    """
    if not train_numbers:
        return TrainEnrichmentResult(
            trains=[],
            status="NOT_ENRICHED",
            error_message="No train numbers provided for enrichment.",
        )

    # Deduplicate while preserving order
    unique_train_numbers = list(dict.fromkeys(train_numbers))
    c = client or QrailClient()

    enriched_list: list[TrainEnrichment] = []
    has_api_error = False
    first_error_msg: Optional[str] = None
    success_count = 0
    failure_count = 0

    for t_num in unique_train_numbers:
        details = enrich_train_details(t_num, client=c)
        running = enrich_train_running_status(t_num, client=c)

        if details.status == "API_ERROR":
            has_api_error = True
            if not first_error_msg:
                first_error_msg = details.error_message
        if running.status == "API_ERROR":
            has_api_error = True
            if not first_error_msg:
                first_error_msg = running.error_message

        # Determine individual train status
        if details.status == "SUCCESS" and running.status == "SUCCESS":
            t_status = "ENRICHED"
            success_count += 1
        elif details.status == "SUCCESS" or running.status == "SUCCESS":
            t_status = "PARTIALLY_ENRICHED"
            success_count += 1
        else:
            t_status = "FAILED"
            failure_count += 1

        enriched_list.append(
            TrainEnrichment(
                train_number=t_num,
                details=details,
                running_status=running,
                status=t_status,
            )
        )

    # Determine overall status
    if success_count == len(unique_train_numbers):
        overall_status = "TRAINS_ENRICHED"
    elif success_count > 0:
        overall_status = "PARTIALLY_ENRICHED"
    elif has_api_error:
        overall_status = "API_ERROR"
    else:
        overall_status = "NOT_ENRICHED"

    return TrainEnrichmentResult(
        trains=enriched_list,
        status=overall_status,
        error_message=first_error_msg if overall_status == "API_ERROR" else None,
    )
