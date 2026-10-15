"""Helpers shared by all services: pagination and translating MySQL errors."""

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

# MySQL error codes we translate into friendly HTTP errors
ER_SIGNAL_EXCEPTION = 1644      # raised by SIGNAL SQLSTATE '45000' in our procedures/triggers
ER_DUP_ENTRY = 1062             # UNIQUE constraint violated
ER_CHECK_CONSTRAINT = 3819      # CHECK constraint violated
ER_NO_REFERENCED_ROW = 1452     # FOREIGN KEY violated


def paginate(db: Session, query, page: int, page_size: int) -> dict:
    """Run a SELECT twice: once to COUNT all matching rows, once for one page (LIMIT/OFFSET)."""
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows = db.execute(query.limit(page_size).offset((page - 1) * page_size))
    first_col = rows.keys()
    items = rows.scalars().all() if len(first_col) == 1 else [dict(r) for r in rows.mappings()]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def raise_for_db_error(exc: DBAPIError):
    """Turn a MySQL error into an HTTP error the frontend can show."""
    code, message = (exc.orig.args + (None, None))[:2] if exc.orig is not None else (None, str(exc))
    if code == ER_SIGNAL_EXCEPTION:
        raise HTTPException(status_code=400, detail=message) from exc
    if code == ER_DUP_ENTRY:
        raise HTTPException(status_code=409, detail=f"Duplicate value: {message}") from exc
    if code in (ER_CHECK_CONSTRAINT, ER_NO_REFERENCED_ROW):
        raise HTTPException(status_code=400, detail=message) from exc
    raise exc
