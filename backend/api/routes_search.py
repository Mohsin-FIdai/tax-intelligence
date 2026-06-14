"""
Tax Intelligence Platform — Search API Routes

Global search endpoint that dispatches to the DataService search engine.
"""

from fastapi import APIRouter, HTTPException, Query

from backend.models.schemas import APIResponse, SearchResult
from backend.services.data_service import DataService

router = APIRouter(prefix="/api/v1/search", tags=["Search"])

ALLOWED_SEARCH_TYPES = {"name", "cnic", "phone", "vehicle", "business"}


@router.get(
    "",
    response_model=APIResponse,
    summary="Global citizen search",
)
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    type: str = Query(  # noqa: A002 — shadowing builtin is intentional for API ergonomics
        "name",
        description="Search type: name, cnic, phone, vehicle, business",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=200, description="Page size"),
) -> APIResponse:
    """Search citizens by name, CNIC, phone number, vehicle registration,
    or business name.

    Returns a paginated ``SearchResult`` payload.
    """
    search_type = type.lower()
    if search_type not in ALLOWED_SEARCH_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid search type '{type}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_SEARCH_TYPES))}"
            ),
        )

    svc = DataService()
    all_results = svc.search_citizens(q, search_type=search_type)
    total_count = len(all_results)

    # Paginate
    start = (page - 1) * page_size
    end = start + page_size
    page_results = all_results[start:end]

    search_result = SearchResult(
        results=page_results,
        total_count=total_count,
        page=page,
        page_size=page_size,
        query=q,
        search_type=search_type,
    )

    return APIResponse(success=True, data=search_result.model_dump())
