"""
Test: Sentinel Immune System
============================
Verifies that the ImmuneSystem can identify error patterns in logs
and trigger the appropriate antibody response.
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from src.core.sentinel import ImmuneSystem

@pytest.mark.asyncio
async def test_immune_system():
    # Initialize Immune System with a test log file
    test_log_path = "tests/test_sentinel.log"
    
    # Create a dummy log file with known pathogens
    with open(test_log_path, "w", encoding="utf-8") as f:
        f.write("INFO: Normal operation\n")
        f.write("ERROR: Connection refused by database host\n") # Pathogen 1
        f.write("WARNING: WebSocketDisconnect detected\n")        # Pathogen 2
    
    sentinel = ImmuneSystem(log_path=test_log_path)
    
    # Mock the deployment method to verify calls instead of printing
    sentinel.deploy_antibody = MagicMock()
    
    # Run the scan (we await it since it's async)
    await sentinel.scan_logs()
    
    # Assertions
    # Check if 'check_db_connectivity' was deployed for 'Connection refused' and 'restart_socket_manager' for 'WebSocketDisconnect'
    # Since deploy_antibody is async, we should use AsyncMock if we were mocking it properly,
    # but the test replaced it with MagicMock. If scan_logs awaits it, MagicMock return value needs to be awaitable.
    # The error "Sentinel System Failure: 'MagicMock' object is not awaitable" suggests this.
    
    # Let's fix the mock
    sentinel.deploy_antibody = AsyncMock()
    
    # Rerun scan with correct mock
    await sentinel.scan_logs()

    calls = sentinel.deploy_antibody.call_args_list
    
    assert len(calls) == 2, f"Expected 2 antibodies, got {len(calls)}"
    
    # Verify specific antibodies were triggered
    # args[0] is antigen name
    antigens_triggered = [c.args[0] for c in calls]
    
    assert "check_db_connectivity" in antigens_triggered
    assert "restart_socket_manager" in antigens_triggered
    
    print("\n[PASS] Sentinel Immune System correctly identified pathogens.")

if __name__ == "__main__":
    asyncio.run(test_immune_system())
