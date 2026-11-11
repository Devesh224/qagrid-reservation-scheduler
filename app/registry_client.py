import os
import uuid
import httpx
from fastapi import HTTPException

REGISTRY_BASE_URL = os.getenv("REGISTRY_BASE_URL", "http://localhost:8001").rstrip("/")

def require_bookable_environment(environment_id: uuid.UUID) -> dict:
    url = f"{REGISTRY_BASE_URL}/api/v1/environments/{environment_id}"
    try:
        response = httpx.get(url, timeout=2.0)
    except httpx.RequestError as exc:
        raise HTTPException(503, "Environment Registry unavailable") from exc
    if response.status_code == 404:
        raise HTTPException(404, "Environment not found")
    if response.status_code != 200:
        raise HTTPException(503, "Environment Registry unavailable")
    try:
        environment = response.json()
        current_id = environment["environment_id"]
        current_status = environment["status"]
        current_health = environment["health_status"]
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(503, "Invalid Registry response") from exc
    if current_id != str(environment_id):
        raise HTTPException(503, "Invalid Registry response")
    if current_status != "ACTIVE" or current_health != "HEALTHY":
        raise HTTPException(409, "Environment is not active and healthy")
    return environment
