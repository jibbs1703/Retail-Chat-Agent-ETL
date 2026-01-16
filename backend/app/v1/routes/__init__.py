"""Retail Product Agent Backend Routes Package."""

from app.v1.routes.healthcheck import router as healthcheck_router
from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(healthcheck_router, tags=["healthcheck"])
