from fastapi import Query, Response

from app.platform.service import apply_pagination_headers, paginate_statement


def page_params():
    return (
        Query(default=1, ge=1, description="1-based page number"),
        Query(default=50, ge=1, le=100, description="Maximum items per page"),
    )


def set_page_headers(response: Response, meta: dict[str, int]) -> None:
    apply_pagination_headers(response, meta)
