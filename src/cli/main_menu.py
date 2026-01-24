"""
VoidCat RDC: Sovereign Spirit - Main Menu
==========================================
Version: 1.1.0
Author: Echo (E-01)
Date: 2026-01-23

Interactive CLI main menu using rich library.
"""

import sys
import asyncio
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt, IntPrompt

console = Console()

# =============================================================================
# ASCII Art Banner
# =============================================================================

BANNER = """
╔═════════════════════════════════════════════════════════════════════════════╗
║                                                                             ║
║ ███████╗ ██████╗ ██╗   ██╗███████╗██████╗ ███████╗██╗ ██████╗ ███╗  ██╗ ║
║ ██╔════╝██╔═══██╗██║   ██║██╔════╝██╔══██╗██╔════╝██║██╔════╝ ████╗ ██║ ║
║ ███████╗██║   ██║██║   ██║█████╗  ██████╔╝█████╗  ██║██║  ███╗ ██╔██╗██║ ║
║ ╚════██║██║   ██║╚██╗ ██╔╝██╔══╝  ██╔══██╗██╔══╝  ██║██║   ██║ ██║╚████║ ║
║ ███████║╚██████╔╝ ╚████╔╝ ███████╗██║  ██║███████╗██║╚██████╔╝ ██║ ╚███║ ║
║ ╚══════╝ ╚═════╝   ╚═══╝  ╚══════╝╚═╝  ╚═╝╚══════╝╚═╝ ╚═════╝  ╚═╝  ╚══╝ ║
║                                                                             ║
║                  ███████╗██████╗ ██╗██████╗ ██╗████████╗                    ║
║                  ██╔════╝██╔══██╗██║██╔══██╗██║╚══██╔══╝                    ║
║                  ███████╗██████╔╝██║██████╔╝██║   ██║                       ║
║                  ╚════██║██╔═══╝ ██║██╔══██╗██║   ██║                       ║
║                  ███████║██║     ██║██║  ██║██║   ██║                       ║
║                  ╚══════╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝   ╚═╝                       ║
║                                                                             ║
║                          VoidCat RDC Control Panel                          ║
╚═════════════════════════════════════════════════════════════════════════════╝
"""

# =============================================================================
# Menu Options
# =============================================================================

MAIN_MENU_OPTIONS = [
    ("1", "Agent Status", "View and manage registered agents"),
    ("6", "Dialogue", "Directly communicate with spirits"),
    ("2", "Heartbeat Logs", "View recent heartbeat activity"),
    ("3", "LLM Configuration", "Configure LLM providers"),
    ("4", "System Health", "Check system and database status"),
    ("5", "Settings", "General configuration"),
    ("Q", "Quit", "Exit the control panel"),
]


def display_banner() -> None:
    """Display the ASCII art banner."""
    console.print(Text(BANNER, style="bold cyan"))


def display_main_menu() -> None:
    """Display the main menu options."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold yellow", width=4)
    table.add_column("Option", style="bold white", width=20)
    table.add_column("Description", style="dim")
    
    for key, option, description in MAIN_MENU_OPTIONS:
        table.add_row(f"[{key}]", option, description)
    
    console.print(Panel(table, title="Main Menu", border_style="blue"))


def get_menu_choice() -> str:
    """Get user's menu choice."""
    return Prompt.ask(
        "\n[bold cyan]Select[/bold cyan]",
        choices=["1", "2", "3", "4", "5", "6", "q", "Q"],
        show_choices=False,
    ).upper()


# =============================================================================
# Menu Handlers
# =============================================================================

async def handle_agent_status() -> None:
    """Handle agent status menu."""
    from src.cli.agents_menu import show_agents_menu
    await show_agents_menu(console)


async def handle_heartbeat_logs() -> None:
    """Handle heartbeat logs menu."""
    from src.cli.logs_menu import show_logs_menu
    await show_logs_menu(console)


async def handle_llm_config() -> None:
    """Handle LLM configuration menu."""
    from src.cli.llm_menu import show_llm_menu
    await show_llm_menu(console)


async def handle_system_health() -> None:
    """Handle system health check."""
    from src.cli.health_menu import show_health_menu
    await show_health_menu(console)


async def handle_settings() -> None:
    """Handle settings menu."""
    from src.cli.settings_menu import show_settings_menu
    await show_settings_menu(console)


# =============================================================================
# Main Loop
# =============================================================================

async def main_loop() -> None:
    """Main interactive loop."""
    while True:
        console.clear()
        display_banner()
        display_main_menu()
        
        choice = get_menu_choice()
        
        if choice == "Q":
            console.print("\n[bold green]Goodbye, my Lord.[/bold green]\n")
            break
        elif choice == "1":
            await handle_agent_status()
        elif choice == "6":
            from src.cli.dialogue_menu import show_dialogue_menu
            await show_dialogue_menu(console)
        elif choice == "2":
            await handle_heartbeat_logs()
        elif choice == "3":
            await handle_llm_config()
        elif choice == "4":
            await handle_system_health()
        elif choice == "5":
            await handle_settings()
        
        # Pause before returning to menu
        if choice != "Q":
            Prompt.ask("\n[dim]Press Enter to continue[/dim]")


def run_cli() -> None:
    """Entry point for the CLI."""
    from src.core.lifecycle import LifecycleManager
    import logging
    
    # Configure logging to prevent TUI corruption
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("neo4j").setLevel(logging.WARNING)
    logging.getLogger("sovereign").setLevel(logging.INFO) # Keep app logs but maybe redirect?
    
    try:
        asyncio.run(main_loop())
    except (KeyboardInterrupt, EOFError):
        console.print("\n[bold yellow]Interrupted. Exiting...[/bold yellow]")
    except Exception as e:
        console.print(f"\n[red]Critical System Error: {e}[/red]")
    finally:
        # manifest the shutdown sequence
        asyncio.run(LifecycleManager.shutdown())
        sys.exit(0)


if __name__ == "__main__":
    run_cli()
