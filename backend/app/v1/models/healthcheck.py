"""Retail Product Agent Backend Healthcheck Models Module."""

from pydantic import BaseModel


class ServiceStatus(BaseModel):
    status: str
    latency_ms: float | None = None
    message: str | None = None


class HealthCheckResponse(BaseModel):
    status: str
    version: str
    postgres: ServiceStatus
    redis: ServiceStatus
    qdrant: ServiceStatus
