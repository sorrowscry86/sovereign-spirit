"""
VoidCat RDC: Sovereign Spirit - Agents Menu
============================================
View and manage registered agents.
"""

import asyncio
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

from src.core.database import get_database


async def show_agents_menu(console: Console) -> None:
    """Display agent status menu."""
    console.clear()
    console.print(Panel("[bold cyan]Agent Status[/bold cyan]", border_style="blue"))
    
    try:
        db = get_database()
        if not db._initialized:
            await db.initialize()
        
        # Query all agents from database
        async with db.session() as session:
            from sqlalchemy import text
            result = await session.execute(
                text("SELECT id, name, designation, current_mood, last_active_at, is_active FROM agents ORDER BY name")
            )
            agents = result.fetchall()
        
        if not agents:
            console.print("[yellow]No agents registered.[/yellow]")
            return
        
        # Create table
        table = Table(title="Registered Agents", show_header=True, header_style="bold magenta", show_lines=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Name", style="cyan")
        table.add_column("Designation", style="dim")
        table.add_column("Archetype", style="italic yellow")
        table.add_column("Mood", style="green")
        table.add_column("Status", style="blue")
        
        for idx, agent in enumerate(agents, 1):
            name = agent.name
            designation = agent.designation or "-"
            
            # Extract Archetype summary
            traits = getattr(agent, 'traits_json', {}) or {}
            archetype = traits.get('archetype', '-')
            if " / " in archetype:
                archetype = archetype.split(" / ")[0] + "..."
            
            mood = agent.current_mood or "Neutral"
            status = "[green]Active[/green]" if agent.is_active else "[red]Disabled[/red]"
            
            table.add_row(str(idx), name, designation, archetype, mood, status)
        
        console.print(table)
        console.print(f"\n[dim]Total: {len(agents)} agent(s)[/dim]")
        
        # Interactive Selection
        from src.core.memory.prism import get_prism
        
        console.print("\nSelect an agent [#] to view their [bold magenta]Memory Prism[/bold magenta] context.")
        choice = Prompt.ask(
            "Enter Number or Name",
            choices=[str(i) for i in range(1, len(agents) + 1)] + [a.name for a in agents] + ["back"],
            default="back"
        )
        
        if choice.lower() != "back":
            # Identify by number or name
            if choice.isdigit() and 1 <= int(choice) <= len(agents):
                selected_agent = agents[int(choice) - 1]
            else:
                selected_agent = next((a for a in agents if a.name.lower() == choice.lower()), None)
            
            if not selected_agent:
                console.print("[red]Invalid selection.[/red]")
                await asyncio.sleep(1)
                return

            selected_name = selected_agent.name
            agent_id = str(selected_agent.id) if hasattr(selected_agent, 'id') else selected_name
            
            console.print(f"\n[bold cyan]Invoking Memory Prism for {selected_name}...[/bold cyan]")
            
            prism = get_prism()
            # Simulate a query
            context = await prism.recall("Status Report", agent_id)
            
            # Display Context
            console.print(Panel(f"[bold]Prism Output (Valence Stripped: {context.valence_stripped})[/bold]", border_style="magenta"))
            
            # --- Persona DNA (SDS v2 Bridge) ---
            try:
                traits = getattr(selected_agent, 'traits_json', {}) or {}
                big_five = traits.get('big_five', {})
                archetype = traits.get('archetype', 'N/A')
                expertise = getattr(selected_agent, 'expertise_tags', []) or []
                
                console.print(f"[bold yellow]Archetype:[/bold yellow] [italic]{archetype}[/italic]")
                if big_five:
                    trait_row = [f"{k.capitalize()}: {v}" for k, v in big_five.items() if v]
                    console.print(f"[bold yellow]Big Five:[/bold yellow] {', '.join(trait_row)}")
                if expertise:
                    console.print(f"[bold yellow]Expertise:[/bold yellow] [blue]{', '.join(expertise)}[/blue]")
                console.print("-" * 40)
            except Exception:
                pass

            # 1. Fast Stream
            console.print("[yellow]Fast Stream (Redis)[/yellow]")
            console.print(f"Session: {context.fast_stream.session_id}")
            console.print(f"Focus: {context.fast_stream.current_focus}")
            
            # 2. Deep Well
            console.print("\n[blue]Deep Well (Weaviate)[/blue]")
            if not context.deep_well:
                console.print("[dim]No episodic memories found.[/dim]")
            for mem in context.deep_well:
                valence_color = "green" if mem.emotional_valence > 0 else "red" if mem.emotional_valence < 0 else "white"
                voice = mem.subjective_voice or "[REDACTED - VALENCE STRIPPED]"
                console.print(f"- {mem.content} | Voice: [{valence_color}]{voice}[/{valence_color}]")
            
            # 3. Crystalline Web
            console.print("\n[green]Crystalline Web (Neo4j)[/green]")
            if not context.crystalline_web:
                console.print("[dim]No task relationships identified.[/dim]")
            for task in context.crystalline_web:
                console.print(f"- [Task {task['id']}] {task['desc']} (P: {task['priority']})")
                
            console.input("\nPress Enter to continue...")
            
    except Exception as e:
        console.print(f"[red]Error loading agents: {e}[/red]")
        console.input("\nPress Enter to continue...")
