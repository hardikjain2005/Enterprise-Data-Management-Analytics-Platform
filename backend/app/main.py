"""
FastAPI application entry point.

    uvicorn app.main:app --reload        (run from the backend/ folder)

Interactive API docs: http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routes import analytics, audit, customers, dashboard, data_quality, etl, health, orders, payments, products

app = FastAPI(
    title="Enterprise Data Management & Analytics Platform API",
    description="REST API over the MySQL database: business data, analytics, ETL monitoring, "
                "data quality and audit logs.",
    version="1.0.0",
)

# Allow the React dev server (another origin/port) to call the API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)

for module in (health, customers, products, orders, payments, dashboard, analytics, data_quality, etl, audit):
    app.include_router(module.router, prefix="/api")


@app.get("/", include_in_schema=False)
def root():
    return {"message": "API is running. See /docs for the endpoint list."}
