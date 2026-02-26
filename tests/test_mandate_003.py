"""
VoidCat RDC: Sovereign Spirit - Mandate 003 Stress Tests
========================================================
Execution of Beatrice's destructive testing profile.
"""

import pytest
import os
import json
import subprocess
from pathlib import Path
from src.core.memory.stasis_chamber import StasisChamber
from wake_protocol import validate_agent_id

@pytest.fixture
def clean_stasis():
    """Ensure a clean stasis environment for tests."""
    dir_path = Path("stasis_tanks_test")
    if dir_path.exists():
        import shutil
        shutil.rmtree(dir_path)
    dir_path.mkdir()
    yield StasisChamber(tank_directory="stasis_tanks_test")
    # Cleanup
    # shutil.rmtree(dir_path)

# --- 1. WAKE PROTOCOL TESTS (THE SPARK) ---

def test_003_WP_01_argument_fuzzing():
    """BEATRICE DO: Shell Injection test."""
    malicious_id = "Beatrice; rm -rf /"
    with pytest.raises(ValueError, match="Suspicious Agent ID Detected"):
        validate_agent_id(malicious_id)

def test_003_WP_01_empty_args():
    """BEATRICE DO: No arguments test."""
    result = subprocess.run(["python", "wake_protocol.py"], capture_output=True, text=True)
    assert "usage:" in result.stdout.lower()
    assert result.returncode == 0

# --- 2. MEMORY TESTS (THE STASIS CHAMBER) ---

def test_003_MC_01_amnesia_attack(clean_stasis):
    """BEATRICE DO: Pointer to non-existent JSON."""
    ptr_file = Path("stasis_tanks_test/broken.ptr")
    with open(ptr_file, "w") as f:
        f.write("C:/NonExistent/tank.json")
    
    # Should not crash, should return empty dict (Cold Boot)
    data = clean_stasis.thaw(str(ptr_file))
    assert data == {}

def test_003_MC_03_malformed_synapse(clean_stasis):
    """BEATRICE DO: Corrupted JSON structure."""
    agent_id = "glados"
    data = {"test": "data"}
    ptr_path = clean_stasis.freeze(agent_id, data)
    
    # Manually corrupt the tank
    with open(Path("stasis_tanks_test/glados_state.json"), "w") as f:
        f.write("{ 'corrupted': true ") # Missing closing brace and bad quotes
        
    # Should not crash, should return empty dict (Cold Boot)
    thawed_data = clean_stasis.thaw(ptr_path)
    assert thawed_data == {}

# --- 3. CHRONOS ADAPTER TESTS (THE HAND) ---

@pytest.mark.asyncio
async def test_003_CP_01_temporal_paradox():
    """BEATRICE DO: Schedule in the past."""
    # We test the PowerShell wrapper directly or via the adapter.
    # PowerShell's New-ScheduledTaskTrigger will likely throw an error 
    # if the date is in the past.
    
    from src.adapters.chronos_adapter import ChronosAdapter
    from unittest.mock import AsyncMock
    
    # Mock MCP to simulate PowerShell behavior
    mock_mcp = AsyncMock()
    mock_mcp.execute_tool = AsyncMock(return_value="PowerShell Error: StartBoundary cannot be in the past.")
    
    adapter = ChronosAdapter(mock_mcp)
    # This is a unit test of the adapter's handling, not the actual OS registration
    result = await adapter.schedule_wake_call("test_agent", -300)
    assert "Error" in result or "cannot be in the past" in result.lower()

if __name__ == "__main__":
    pytest.main([__file__])
