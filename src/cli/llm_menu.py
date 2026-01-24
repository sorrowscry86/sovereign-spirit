"""
VoidCat RDC: Sovereign Spirit - LLM Menu
=========================================
Configure LLM providers.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from src.core.llm_client import get_llm_client, ProviderType
from src.core.llm_config import load_config, save_config


async def show_llm_menu(console: Console) -> None:
    """Display LLM configuration menu."""
    console.clear()
    console.print(Panel("[bold cyan]LLM Configuration[/bold cyan]", border_style="blue"))
    
    client = get_llm_client()
    config = load_config()
    
    # Show current configuration
    console.print(f"\n[bold]Active Provider:[/bold] [green]{client.active_provider}[/green]")
    console.print(f"[bold]Fallback Chain:[/bold] {' → '.join(client.fallback_chain)}")
    
    # Provider table
    table = Table(title="\nConfigured Providers", show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="dim")
    table.add_column("Endpoint", style="white")
    table.add_column("Model", style="yellow")
    table.add_column("Status", style="green")
    
    for name, provider in client.providers.items():
        status = "[green]●[/green]" if name == client.active_provider else "[dim]○[/dim]"
        endpoint = provider.endpoint[:40] + "..." if len(provider.endpoint) > 40 else provider.endpoint
        
        table.add_row(
            name,
            provider.provider_type.value,
            endpoint,
            provider.model,
            status
        )
    
    console.print(table)
    
    # Menu options
    console.print("\n[bold]Options:[/bold]")
    console.print("  [1] Switch active provider")
    console.print("  [2] Test provider connection")
    console.print("  [3] Back to main menu")
    
    choice = Prompt.ask("\nSelect", choices=["1", "2", "3"], default="3")
    
    if choice == "1":
        await switch_provider(console, client, config)
    elif choice == "2":
        await test_provider(console, client)


async def switch_provider(console: Console, client, config) -> None:
    """Switch the active LLM provider."""
    provider_names = list(client.providers.keys())
    
    console.print("\n[bold]Available providers:[/bold]")
    for i, name in enumerate(provider_names, 1):
        console.print(f"  [{i}] {name}")
    
    choice = Prompt.ask("Select provider number", default="1")
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(provider_names):
            new_provider = provider_names[idx]
            client.set_active_provider(new_provider)
            config.active_provider = new_provider
            save_config(config)
            console.print(f"\n[green]✓ Active provider set to: {new_provider}[/green]")
        else:
            console.print("[red]Invalid selection[/red]")
    except ValueError:
        console.print("[red]Invalid input[/red]")


async def test_provider(console: Console, client) -> None:
    """Test connection to a provider."""
    provider_names = list(client.providers.keys())
    
    console.print("\n[bold]Select provider to test:[/bold]")
    for i, name in enumerate(provider_names, 1):
        console.print(f"  [{i}] {name}")
    
    choice = Prompt.ask("Select provider number", default="1")
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(provider_names):
            provider_name = provider_names[idx]
            console.print(f"\n[dim]Testing {provider_name}...[/dim]")
            
            is_available = await client.health_check(provider_name)
            
            if is_available:
                console.print(f"[green]✓ {provider_name} is available[/green]")
            else:
                console.print(f"[red]✗ {provider_name} is not available[/red]")
        else:
            console.print("[red]Invalid selection[/red]")
    except ValueError:
        console.print("[red]Invalid input[/red]")
