from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..database import get_db

router = APIRouter(tags=["Health"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    """Checks that the API is up AND can talk to MySQL."""
    try:
        version = db.execute(text("SELECT VERSION()")).scalar()
        database = db.execute(text("SELECT DATABASE()")).scalar()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc.__class__.__name__}")
    return {"status": "ok", "database": database, "mysql_version": version}
