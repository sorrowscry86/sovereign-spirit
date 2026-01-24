"""
VoidCat RDC: Sovereign Spirit - Logs Menu
==========================================
View recent heartbeat activity logs.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import IntPrompt

from src.core.database import get_database


async def show_logs_menu(console: Console) -> None:
    """Display heartbeat logs menu."""
    console.clear()
    console.print(Panel("[bold cyan]Heartbeat Logs[/bold cyan]", border_style="blue"))
    
    limit = IntPrompt.ask("Number of logs to display", default=20)
    
    try:
        db = get_database()
        if not db._initialized:
            await db.initialize()
        
        # Query recent heartbeat logs
        async with db.session() as session:
            from sqlalchemy import text
            result = await session.execute(
                text("""
                    SELECT h.id, a.name as agent_name, h.action_taken, h.thought_content, h.created_at
                    FROM heartbeat_logs h
                    JOIN agents a ON h.agent_id = a.id
                    ORDER BY h.created_at DESC
                    LIMIT :limit
                """),
                {"limit": limit}
            )
            logs = result.fetchall()
        
        if not logs:
            console.print("[yellow]No heartbeat logs found.[/yellow]")
            return
        
        # Create table
        table = Table(title="Recent Heartbeat Activity", show_header=True, header_style="bold magenta")
        table.add_column("Time", style="dim", width=19)
        table.add_column("Agent", style="cyan", width=12)
        table.add_column("Action", style="green", width=8)
        table.add_column("Details", style="white")
        
        for log in logs:
            time_str = str(log.created_at)[:19] if log.created_at else "-"
            agent = log.agent_name or "-"
            action = log.action_taken or "-"
            details = (log.thought_content or "-")[:50]
            
            # Color code actions
            if action == "SLEEP":
                action = f"[dim]{action}[/dim]"
            elif action == "ACT":
                action = f"[bold green]{action}[/bold green]"
            elif action == "ERROR":
                action = f"[bold red]{action}[/bold red]"
            
            table.add_row(time_str, agent, action, details)
        
    except Exception as e:
        console.print(f"[red]Error loading logs: {e}[/red]")
        return

    # Visual Timeline Option
    from rich.prompt import Prompt
    console.print("\nOptions:")
    console.print("1. Refresh Logs")
    console.print("2. Generate Visual Timeline (HTML)")
    console.print("B. Back")
    
    choice = Prompt.ask("Select", choices=["1", "2", "B", "b"], default="B")
    
    if choice == "1":
        await show_logs_menu(console)
    elif choice == "2":
        from src.core.chronicler import get_chronicler
        from src.core.visualization.timeline_renderer import TimelineRenderer
        
        with console.status("[bold green]Weaving the Chronicles...[/bold green]"):
            chronicler = get_chronicler()
            events = await chronicler.get_timeline(limit=200)
            
            renderer = TimelineRenderer()
            output_path = renderer.generate_html_report(events)
            
        console.print(f"\n[bold green]Success![/bold green] Timeline generated at: [link=file:///{output_path}]{output_path}[/link]")
        import os
        # startfile only on windows
        if os.name == 'nt':
            os.startfile(output_path)
            
        console.input("\nPress Enter to return...")
