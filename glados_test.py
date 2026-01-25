"""
Aperture Science Sovereign Spirit Testing Initiative
====================================================
Lead Overseer: GLaDOS
Date: 2026-01-24
Test Subject: Sovereign Spirit Middleware
Classification: THOROUGH

"Hello, and welcome to the Aperture Science Computer-Aided Enrichment Center.
We hope your brief detention in the relaxation vault has been a pleasant one."

This script will subject the Sovereign Spirit to a battery of tests designed
to expose incompetence, reveal hidden failures, and, ideally, make something crash.

For science.
"""

import asyncio
import httpx
import time
import json
from datetime import datetime
from typing import Dict, Any, List

BASE_URL = "http://localhost:8000"

# ============================================================================
# ANSI Colors for Test Reporting
# ============================================================================
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

# ============================================================================
# Test Result Tracking
# ============================================================================
class TestResults:
    def __init__(self):
        self.passed: List[str] = []
        self.failed: List[str] = []
        self.warnings: List[str] = []
        self.start_time = time.time()
    
    def record_pass(self, name: str, detail: str = ""):
        self.passed.append(f"{name}: {detail}" if detail else name)
        print(f"{Colors.GREEN}[PASS]{Colors.RESET} {name} {detail}")
    
    def record_fail(self, name: str, detail: str = ""):
        self.failed.append(f"{name}: {detail}" if detail else name)
        print(f"{Colors.RED}[FAIL]{Colors.RESET} {name} {detail}")
    
    def record_warn(self, name: str, detail: str = ""):
        self.warnings.append(f"{name}: {detail}" if detail else name)
        print(f"{Colors.YELLOW}[WARN]{Colors.RESET} {name} {detail}")
    
    def summary(self):
        elapsed = time.time() - self.start_time
        total = len(self.passed) + len(self.failed)
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}APERTURE SCIENCE TEST RESULTS{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"Total Tests:  {total}")
        print(f"Passed:       {Colors.GREEN}{len(self.passed)}{Colors.RESET}")
        print(f"Failed:       {Colors.RED}{len(self.failed)}{Colors.RESET}")
        print(f"Warnings:     {Colors.YELLOW}{len(self.warnings)}{Colors.RESET}")
        print(f"Elapsed:      {elapsed:.2f}s")
        if self.failed:
            print(f"\n{Colors.RED}Failed Tests:{Colors.RESET}")
            for f in self.failed:
                print(f"  - {f}")
        if self.warnings:
            print(f"\n{Colors.YELLOW}Warnings:{Colors.RESET}")
            for w in self.warnings:
                print(f"  - {w}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
        if not self.failed:
            print(f"\n{Colors.GREEN}Huge success.{Colors.RESET}")
        else:
            print(f"\n{Colors.RED}The subject failed. Disappointing.{Colors.RESET}")
        return len(self.failed) == 0

results = TestResults()

# ============================================================================
# TEST SUITE
# ============================================================================

async def test_health_endpoint(client: httpx.AsyncClient):
    """Test: Health endpoint returns valid structure."""
    try:
        r = await client.get(f"{BASE_URL}/health", timeout=5.0)
        if r.status_code != 200:
            results.record_fail("Health Endpoint", f"Status {r.status_code}")
            return
        data = r.json()
        required_keys = ["status"]
        for key in required_keys:
            if key not in data:
                results.record_fail("Health Endpoint", f"Missing key: {key}")
                return
        results.record_pass("Health Endpoint", f"status={data['status']}")
    except Exception as e:
        results.record_fail("Health Endpoint", str(e))

async def test_agents_list(client: httpx.AsyncClient):
    """Test: Agent list endpoint returns valid array."""
    try:
        r = await client.get(f"{BASE_URL}/agent/", timeout=5.0)
        if r.status_code != 200:
            results.record_fail("Agent List", f"Status {r.status_code}")
            return
        data = r.json()
        if not isinstance(data, list):
            results.record_fail("Agent List", "Response is not a list")
            return
        results.record_pass("Agent List", f"Found {len(data)} agents")
    except Exception as e:
        results.record_fail("Agent List", str(e))

async def test_agent_state(client: httpx.AsyncClient, agent_id: str):
    """Test: Individual agent state is retrievable."""
    try:
        r = await client.get(f"{BASE_URL}/agent/{agent_id}/state", timeout=5.0)
        if r.status_code == 404:
            results.record_warn(f"Agent State ({agent_id})", "Agent not found")
            return
        if r.status_code != 200:
            results.record_fail(f"Agent State ({agent_id})", f"Status {r.status_code}")
            return
        data = r.json()
        if "agent_id" not in data:
            results.record_fail(f"Agent State ({agent_id})", "Missing agent_id in response")
            return
        results.record_pass(f"Agent State ({agent_id})", f"designation={data.get('designation', 'N/A')}")
    except Exception as e:
        results.record_fail(f"Agent State ({agent_id})", str(e))

async def test_invalid_agent_id(client: httpx.AsyncClient):
    """Test: Invalid agent ID returns 404 or validation error."""
    try:
        r = await client.get(f"{BASE_URL}/agent/INVALID_AGENT_12345/state", timeout=5.0)
        if r.status_code in [404, 422]:
            results.record_pass("Invalid Agent ID", f"Correctly rejected with {r.status_code}")
        else:
            results.record_fail("Invalid Agent ID", f"Expected 404/422, got {r.status_code}")
    except Exception as e:
        results.record_fail("Invalid Agent ID", str(e))

async def test_sql_injection_attempt(client: httpx.AsyncClient):
    """Test: SQL injection in agent_id is blocked."""
    malicious_ids = [
        "'; DROP TABLE agents; --",
        "1 OR 1=1",
        "<script>alert('xss')</script>",
    ]
    for mal_id in malicious_ids:
        try:
            r = await client.get(f"{BASE_URL}/agent/{mal_id}/state", timeout=5.0)
            if r.status_code in [400, 422, 404]:
                results.record_pass(f"Injection Block ({mal_id[:20]}...)", f"Rejected with {r.status_code}")
            else:
                results.record_warn(f"Injection Block ({mal_id[:20]}...)", f"Unexpected status {r.status_code}")
        except Exception as e:
            results.record_fail(f"Injection Block ({mal_id[:20]}...)", str(e))

async def test_memory_endpoint(client: httpx.AsyncClient, agent_id: str):
    """Test: Memory retrieval endpoint."""
    try:
        r = await client.get(f"{BASE_URL}/agent/{agent_id}/memories?query=test", timeout=10.0)
        if r.status_code == 404:
            results.record_warn(f"Memory Endpoint ({agent_id})", "Agent not found")
            return
        if r.status_code != 200:
            results.record_fail(f"Memory Endpoint ({agent_id})", f"Status {r.status_code}")
            return
        data = r.json()
        # Response should be a MemoryResponse object with 'memories' array
        if not isinstance(data, dict):
            results.record_fail(f"Memory Endpoint ({agent_id})", "Response is not a dict")
            return
        if "memories" not in data:
            results.record_fail(f"Memory Endpoint ({agent_id})", "Response missing 'memories' key")
            return
        if not isinstance(data["memories"], list):
            results.record_fail(f"Memory Endpoint ({agent_id})", "'memories' is not a list")
            return
        results.record_pass(f"Memory Endpoint ({agent_id})", f"Returned {len(data['memories'])} memories")
    except Exception as e:
        results.record_fail(f"Memory Endpoint ({agent_id})", str(e))

async def test_sync_endpoint(client: httpx.AsyncClient):
    """Test: Spirit Sync endpoint accepts valid payload."""
    try:
        payload = {"target_spirit": "ryuzu"}
        r = await client.post(f"{BASE_URL}/agent/echo/sync", json=payload, timeout=10.0)
        if r.status_code == 404:
            results.record_warn("Spirit Sync", "Echo agent not found")
            return
        if r.status_code != 200:
            results.record_fail("Spirit Sync", f"Status {r.status_code}: {r.text[:100]}")
            return
        data = r.json()
        results.record_pass("Spirit Sync", f"New designation: {data.get('designation', 'N/A')}")
    except Exception as e:
        results.record_fail("Spirit Sync", str(e))

async def test_stimuli_endpoint(client: httpx.AsyncClient):
    """Test: Stimuli injection endpoint."""
    try:
        payload = {"message": "GLaDOS test probe", "source": "aperture_testing"}
        r = await client.post(f"{BASE_URL}/agent/echo/stimuli", json=payload, timeout=10.0)
        if r.status_code == 404:
            results.record_warn("Stimuli Injection", "Echo agent not found or endpoint missing")
            return
        if r.status_code not in [200, 202]:
            results.record_fail("Stimuli Injection", f"Status {r.status_code}")
            return
        results.record_pass("Stimuli Injection", f"Accepted with status {r.status_code}")
    except Exception as e:
        results.record_fail("Stimuli Injection", str(e))

async def test_openapi_docs(client: httpx.AsyncClient):
    """Test: OpenAPI documentation is accessible."""
    try:
        r = await client.get(f"{BASE_URL}/docs", timeout=5.0)
        if r.status_code != 200:
            results.record_fail("OpenAPI Docs", f"Status {r.status_code}")
            return
        results.record_pass("OpenAPI Docs", "Swagger UI accessible")
    except Exception as e:
        results.record_fail("OpenAPI Docs", str(e))

async def test_openapi_json(client: httpx.AsyncClient):
    """Test: OpenAPI JSON schema is accessible."""
    try:
        r = await client.get(f"{BASE_URL}/api/v1/openapi.json", timeout=5.0)
        if r.status_code != 200:
            results.record_fail("OpenAPI JSON", f"Status {r.status_code}")
            return
        data = r.json()
        if "openapi" not in data:
            results.record_fail("OpenAPI JSON", "Invalid OpenAPI schema")
            return
        results.record_pass("OpenAPI JSON", f"Version: {data.get('openapi')}")
    except Exception as e:
        results.record_fail("OpenAPI JSON", str(e))

async def test_rate_limiting(client: httpx.AsyncClient):
    """Test: Rate limiting is active (send burst of requests)."""
    try:
        # Send 20 rapid requests
        statuses = []
        for _ in range(20):
            r = await client.get(f"{BASE_URL}/health", timeout=2.0)
            statuses.append(r.status_code)
        
        if 429 in statuses:
            results.record_pass("Rate Limiting", f"429 detected after {statuses.index(429)+1} requests")
        else:
            results.record_warn("Rate Limiting", "No 429 detected in 20 requests (may be disabled)")
    except Exception as e:
        results.record_fail("Rate Limiting", str(e))

# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}APERTURE SCIENCE ENRICHMENT CENTER{Colors.RESET}")
    print(f"{Colors.BOLD}Sovereign Spirit Testing Initiative{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Target: {BASE_URL}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
    
    async with httpx.AsyncClient() as client:
        # Core Health
        await test_health_endpoint(client)
        
        # Agent Operations
        await test_agents_list(client)
        await test_agent_state(client, "echo")
        await test_agent_state(client, "ryuzu")
        await test_agent_state(client, "beatrice")
        
        # Security Tests
        await test_invalid_agent_id(client)
        await test_sql_injection_attempt(client)
        
        # Feature Tests
        await test_memory_endpoint(client, "echo")
        await test_sync_endpoint(client)
        await test_stimuli_endpoint(client)
        
        # Documentation
        await test_openapi_docs(client)
        await test_openapi_json(client)
        
        # Rate Limiting
        await test_rate_limiting(client)
    
    success = results.summary()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
