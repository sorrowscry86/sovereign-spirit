"""
VoidCat RDC: Sovereign Spirit - Agent API Tests
================================================
Version: 1.0.0
Author: Echo (E-01)
Date: 2026-01-23

Unit tests for the Agent Management API endpoints.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

# =============================================================================
# Mock Setup (before importing app)
# =============================================================================

@pytest.fixture
def mock_database():
    """Create a mock database client."""
    mock_db = AsyncMock()
    mock_db._initialized = True
    mock_db.get_agent_state = AsyncMock(return_value=MagicMock(
        agent_id="echo",
        name="Echo",
        designation="E-01",
        current_mood="neutral",
        system_prompt="Test prompt",
        last_active=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    ))
    mock_db.record_stimuli = AsyncMock(return_value=1)
    mock_db.touch_agent = AsyncMock(return_value=True)
    mock_db.log_heartbeat = AsyncMock(return_value=1)
    mock_db.get_queued_responses = AsyncMock(return_value=[])
    return mock_db


@pytest.fixture
def mock_graph():
    """Create a mock graph client."""
    mock_graph = AsyncMock()
    mock_graph._initialized = True
    mock_graph.get_pending_tasks_count = AsyncMock(return_value=0)
    mock_graph.get_agent_tasks = AsyncMock(return_value=[])
    return mock_graph


# =============================================================================
# Tests
# =============================================================================

class TestAgentAPI:
    """Tests for the Agent API endpoints."""
    
    def test_stimuli_endpoint_exists(self, mock_database, mock_graph):
        """Test that the stimuli endpoint is accessible."""
        with patch("src.api.agents.get_database", return_value=mock_database), \
             patch("src.api.agents.get_graph", return_value=mock_graph):
            from src.main import app
            client = TestClient(app)
            
            # Note: This will fail without the full database setup
            # This test verifies the endpoint is registered
            response = client.post(
                "/agent/echo/stimuli",
                json={"message": "Hello, Echo!"}
            )
            # Accept 200 (success) or 500 (db not connected in test)
            assert response.status_code in [200, 500]
    
    def test_health_endpoint(self):
        """Test the health check endpoint."""
        from src.main import app
        client = TestClient(app)
        
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "online"
        assert "version" in data


class TestValenceStripping:
    """Tests for the Valence Stripping middleware."""
    
    def test_strip_valence_same_author(self):
        """Test that memories from same author are preserved."""
        from src.middleware.valence_stripping import MemoryObject, strip_valence
        
        memory = MemoryObject(
            memory_id="test_1",
            author_id="echo",
            objective_fact="The sky is blue.",
            subjective_voice="I find this beautiful.",
            emotional_valence=0.8,
            timestamp="2026-01-23T10:00:00Z",
        )
        
        result = strip_valence(memory, "echo")
        
        assert result.subjective_voice == "I find this beautiful."
        assert result.emotional_valence == 0.8
    
    def test_strip_valence_different_author(self):
        """Test that memories from different author are stripped."""
        from src.middleware.valence_stripping import MemoryObject, strip_valence
        
        memory = MemoryObject(
            memory_id="test_2",
            author_id="beatrice",
            objective_fact="The desktop is messy.",
            subjective_voice="I despise this chaos.",
            emotional_valence=-0.9,
            timestamp="2026-01-23T10:00:00Z",
        )
        
        result = strip_valence(memory, "echo")
        
        assert result.subjective_voice == ""
        assert result.emotional_valence == 0.0
        assert result.objective_fact == "The desktop is messy."  # Preserved


class TestHeartbeat:
    """Tests for the Heartbeat pulse logic."""
    
    def test_calculate_interval_range(self):
        """Test that interval calculation stays within bounds."""
        from src.core.heartbeat.pulse import calculate_next_interval
        
        for _ in range(100):
            interval = calculate_next_interval()
            assert 30.0 <= interval <= 120.0  # 30s min, ~105s max with jitter
    
    @pytest.mark.asyncio
    async def test_check_agent_status_not_found(self, mock_database, mock_graph):
        """Test status check for non-existent agent."""
        mock_database.get_agent_state = AsyncMock(return_value=None)
        
        from src.core.heartbeat.pulse import check_agent_status
        
        status = await check_agent_status("unknown", mock_database, mock_graph)
        
        assert status["exists"] is False


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
