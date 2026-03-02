"""
Tests for Projects DatabaseClient methods.
Requires a live Postgres connection — run against the Docker database.
"""

import pytest
from src.core.database import get_database


@pytest.mark.asyncio
async def test_create_and_get_project():
    db = get_database()
    await db.initialize()
    project_id = await db.create_project(
        title="Test Project",
        description="A test project for the build",
        lead_agent_id="echo",
    )
    assert project_id != ""

    project = await db.get_project(project_id)
    assert project["title"] == "Test Project"
    assert project["status"] == "active"
    assert project["progress_notes"] == ""


@pytest.mark.asyncio
async def test_list_projects():
    db = get_database()
    await db.initialize()
    projects = await db.list_projects(status="active")
    assert isinstance(projects, list)


@pytest.mark.asyncio
async def test_append_project_progress():
    db = get_database()
    await db.initialize()
    project_id = await db.create_project(
        title="Progress Test",
        description="Testing progress notes",
        lead_agent_id="echo",
    )
    await db.append_project_progress(project_id, "Completed step 1.")
    project = await db.get_project(project_id)
    assert "Completed step 1." in project["progress_notes"]


@pytest.mark.asyncio
async def test_update_project_status():
    db = get_database()
    await db.initialize()
    project_id = await db.create_project(
        title="Status Test",
        description="Testing status update",
        lead_agent_id="echo",
    )
    await db.update_project_status(project_id, "paused")
    project = await db.get_project(project_id)
    assert project["status"] == "paused"
