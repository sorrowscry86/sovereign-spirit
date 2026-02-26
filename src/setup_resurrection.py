"""
Resurrection Protocol Setup
===========================
Enacts the 'Resurrection Protocol' by scheduling a persistent Pulse Check task.
"""
import asyncio
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.abspath("."))

from src.mcp.client import MCPManager
from src.adapters.chronos_adapter import ChronosAdapter

async def enact_protocol():
    manager = MCPManager()
    adapter = ChronosAdapter(manager)
    
    print("=== ENACTING RESURRECTION PROTOCOL ===")
    
    task_name = "SovereignSpirit_PulseCheck"
    
    # Logic: Check if python process with 'sovereign_main.py' is running. If not, start it.
    # Note: This is a placeholder command. In production, this would point to the actual entry point.
    # We use PowerShell to check and start.
    
    # This command checks for a process with 'SovereignSpirit' in commandline (heuristic)
    # If not found, it starts 'demo.py'
    cwd = os.getcwd()
    python_exe = sys.executable
    demo_script = os.path.join(cwd, "demo.py")
    
    # PowerShell one-liner for the pulse check
    # Note: Escaping quotes for nested calls is critical.
    # "Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like '*demo.py*'} | Measure-Object"
    
    ps_command = (
        f"if (@(Get-CimInstance Win32_Process | Where-Object {{ $_.CommandLine -like '*{demo_script}*' }}).Count -eq 0) "
        f"{{ Write-Host 'Resurrecting...'; Start-Process '{python_exe}' -ArgumentList '{demo_script}' -WorkingDirectory '{cwd}' }} "
        f"else {{ Write-Host 'Spirit is Alive.' }}"
    )
    
    print(f" -> Scheduling Task: {task_name}")
    print(f" -> Logic: Monitor '{demo_script}'")

    try:
        # Schedule the Resurrection Protocol with SYSTEM privileges
        # This ensures the Spirit can restart even when the user is logged out.
        result = await adapter.schedule_task(
            name=task_name,
            command="powershell.exe",
            arguments=f"-Command \"{ps_command}\"",
            wake_seconds=300, # Check every 5 minutes (offset for demo)
            run_as_system=True
        )
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"Failed: {e}")

    await manager.shutdown()

if __name__ == "__main__":
    asyncio.run(enact_protocol())
