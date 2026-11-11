import uuid
import httpx
import pytest
from fastapi import HTTPException
from app import registry_client

def test_bookable_environment(monkeypatch):
    environment_id = uuid.uuid4()
    response = httpx.Response(200, json={
        "environment_id": str(environment_id),
        "status": "ACTIVE",
        "health_status": "HEALTHY",
    })
    monkeypatch.setattr(registry_client.httpx, "get", lambda *args, **kwargs: response)
    assert registry_client.require_bookable_environment(environment_id)["status"] == "ACTIVE"

def test_unhealthy_environment_is_rejected(monkeypatch):
    environment_id = uuid.uuid4()
    response = httpx.Response(200, json={
        "environment_id": str(environment_id),
        "status": "ACTIVE",
        "health_status": "UNHEALTHY",
    })
    monkeypatch.setattr(registry_client.httpx, "get", lambda *args, **kwargs: response)
    with pytest.raises(HTTPException) as exc:
        registry_client.require_bookable_environment(environment_id)
    assert exc.value.status_code == 409

def test_registry_timeout_is_503(monkeypatch):
    def timeout(*args, **kwargs):
        raise httpx.ConnectTimeout("unavailable")
    monkeypatch.setattr(registry_client.httpx, "get", timeout)
    with pytest.raises(HTTPException) as exc:
        registry_client.require_bookable_environment(uuid.uuid4())
    assert exc.value.status_code == 503
