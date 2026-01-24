"""
VoidCat RDC: Sovereign Spirit - Settings Menu
==============================================
General configuration settings.
"""

import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from src.core.llm_config import load_config, save_config


async def show_settings_menu(console: Console) -> None:
    """Display settings menu."""
    console.clear()
    console.print(Panel("[bold cyan]Settings[/bold cyan]", border_style="blue"))
    
    # Load current config
    config = load_config()
    
    # Display current settings
    table = Table(title="Current Configuration", show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    # Heartbeat settings
    table.add_row("Heartbeat Interval", f"{os.getenv('HEARTBEAT_INTERVAL_MS', '90000')} ms")
    table.add_row("Heartbeat Jitter", f"{os.getenv('HEARTBEAT_JITTER_MS', '15000')} ms")
    table.add_row("Max Tokens", os.getenv('HEARTBEAT_MAX_TOKENS', '75'))
    table.add_row("Temperature", os.getenv('HEARTBEAT_TEMPERATURE', '0.6'))
    
    # LLM settings
    table.add_row("Active LLM Provider", config.active_provider)
    table.add_row("Fallback Chain", " → ".join(config.fallback_chain))
    
    console.print(table)
    
    # Menu options
    console.print("\n[bold]Options:[/bold]")
    console.print("  [1] Edit heartbeat interval")
    console.print("  [2] Edit LLM fallback chain")
    console.print("  [3] View environment variables")
    console.print("  [4] Back to main menu")
    
    choice = Prompt.ask("\nSelect", choices=["1", "2", "3", "4"], default="4")
    
    if choice == "1":
        await edit_heartbeat_interval(console)
    elif choice == "2":
        await edit_fallback_chain(console, config)
    elif choice == "3":
        show_env_vars(console)


async def edit_heartbeat_interval(console: Console) -> None:
    """Edit heartbeat interval setting."""
    console.print("\n[yellow]Note: This requires editing config/.env and restarting the service.[/yellow]")
    console.print(f"Current interval: {os.getenv('HEARTBEAT_INTERVAL_MS', '90000')} ms")
    
    new_interval = Prompt.ask("New interval (ms)", default="90000")
    console.print(f"\n[dim]To apply, add to config/.env: HEARTBEAT_INTERVAL_MS={new_interval}[/dim]")


async def edit_fallback_chain(console: Console, config) -> None:
    """Edit LLM fallback chain."""
    console.print(f"\nCurrent chain: {' → '.join(config.fallback_chain)}")
    console.print("\nEnter provider names separated by commas:")
    console.print("[dim]Available: ollama_local, lm_studio, openrouter, openai[/dim]")
    
    new_chain = Prompt.ask("Fallback chain", default=",".join(config.fallback_chain))
    
    providers = [p.strip() for p in new_chain.split(",") if p.strip()]
    
    if Confirm.ask(f"Set fallback chain to: {' → '.join(providers)}?"):
        config.fallback_chain = providers
        save_config(config)
        console.print("[green]✓ Fallback chain updated[/green]")


def show_env_vars(console: Console) -> None:
    """Display relevant environment variables."""
    env_vars = [
        "OLLAMA_HOST",
        "OLLAMA_MODEL",
        "LM_STUDIO_HOST",
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
        "HEARTBEAT_INTERVAL_MS",
        "HEARTBEAT_JITTER_MS",
        "HEARTBEAT_MAX_TOKENS",
        "HEARTBEAT_TEMPERATURE",
    ]
    
    table = Table(title="\nEnvironment Variables", show_header=True, header_style="bold magenta")
    table.add_column("Variable", style="cyan")
    table.add_column("Value", style="green")
    
    for var in env_vars:
        value = os.getenv(var)
        if value is None:
            display = "[dim]Not set[/dim]"
        elif "KEY" in var or "PASSWORD" in var:
            display = "[dim]***[/dim]" if value else "[dim]Not set[/dim]"
        else:
            display = value
        table.add_row(var, display)
    
    console.print(table)
