"""
Tests for /api/projects/ endpoints.
Requires live DB — runs against Docker stack via ASGI transport.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app

HEADERS = {"X-API-Key": "voidcat-secure-handshake-2026"}


@pytest.mark.asyncio
async def test_create_project():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/projects/",
            json={
                "title": "API Test Project",
                "description": "Testing the projects endpoint",
                "lead_agent_id": "echo",
            },
            headers=HEADERS,
        )
    assert resp.status_code == 201
    data = resp.json()
    assert "project_id" in data
    assert data["title"] == "API Test Project"


@pytest.mark.asyncio
async def test_list_projects():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/projects/", headers=HEADERS)
    assert resp.status_code == 200
    assert "projects" in resp.json()


@pytest.mark.asyncio
async def test_get_project_detail():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create = await client.post(
            "/api/projects/",
            json={
                "title": "Detail Test",
                "description": "For get test",
                "lead_agent_id": "echo",
            },
            headers=HEADERS,
        )
        project_id = create.json()["project_id"]
        resp = await client.get(f"/api/projects/{project_id}", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["project_id"] == project_id
