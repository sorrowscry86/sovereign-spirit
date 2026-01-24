"""
VoidCat RDC: Sovereign Spirit - Dialogue Menu
==============================================
Interactive chat interface for multi-turn agent interaction.
"""

import asyncio
import logging
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.live import Live
from rich.text import Text

from src.core.database import get_database
from src.core.memory.prism import get_prism
from src.core.inference.prompts import build_system_prompt
from src.core.llm_client import get_llm_client

logger = logging.getLogger("sovereign.cli.dialogue")

async def show_dialogue_menu(console: Console) -> None:
    """Entry point for the Dialogue system."""
    console.clear()
    console.print(Panel("[bold green]Sanctum of Dialogue[/bold green]", border_style="green"))
    
    try:
        db = get_database()
        if not db._initialized: await db.initialize()
        
        async with db.session() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT id, name, designation, archetype, traits_json, behavior_modes FROM agents WHERE is_active = true ORDER BY name"))
            agents = result.fetchall()
            
        if not agents:
            console.print("[red]No active agents found in the Pantheon.[/red]")
            console.input("\nPress Enter to return...")
            return
            
        # Agent Selection
        console.print("Select a Spirit to manifest:")
        choices = [f"{i}. {a.name}" for i, a in enumerate(agents, 1)]
        for c in choices: console.print(c)
        
        c_idx = Prompt.ask("\nSpirit #", choices=[str(i) for i in range(1, len(agents) + 1)] + ["back"], default="back")
        if c_idx == "back": return
        
        agent = agents[int(c_idx) - 1]
        await run_chat_loop(console, agent)
        
    except Exception as e:
        console.print(f"[red]Dialogue Initialization Failed: {e}[/red]")
        console.input("\nPress Enter to continue...")

async def run_chat_loop(console: Console, agent: Any) -> None:
    """Main interactive chat loop."""
    prism = get_prism()
    llm = get_llm_client()
    
    agent_id = str(agent.id)
    agent_name = agent.name
    session_id = f"cli_chat_{agent_id}"
    
    console.clear()
    console.print(Panel(f"Interface established with [bold cyan]{agent_name}[/bold cyan] ({agent.designation})", border_style="cyan"))
    console.print("[dim]Type 'exit' to close the connection.[/dim]\n")
    
    while True:
        user_input = Prompt.ask(f"[bold white]{os.getlogin()}[/bold white]")
        if user_input.lower() in ["exit", "quit", "back"]:
            break
            
        # 1. Prism Recall (Semantic Context + Working Memory)
        with console.status(f"[italic]Querying Memory Prism for {agent_name}...[/italic]"):
            context = await prism.recall(user_input, agent_id, session_id=session_id)
            
        # 2. Add to Fast Stream (Live Input)
        await prism.add_chat_message(session_id, "User", user_input)
        
        # 3. LLM Inference (Manners Protocol Aware)
        import json
        raw_traits = agent.traits_json
        logger.debug(f"Parsing traits for {agent_name}. Type: {type(raw_traits)}")

        if isinstance(raw_traits, str):
            traits = json.loads(raw_traits)
        elif isinstance(raw_traits, (dict, list)):
            traits = raw_traits
        else:
            traits = {}
        
        # Build high-fidelity system prompt
        system_prompt = build_system_prompt(
            agent_name=agent_name,
            designation=agent.designation,
            archetype=agent.archetype or "General Spirit",
            traits=traits
        )
        
        # Append Memory Context
        system_prompt += "\n### MEMORY CONTEXT (Episodic)\n"
        for mem in context.deep_well:
            system_prompt += f"- {mem.content}\n"
            
        from src.core.llm_client import ChatMessage
        history = context.fast_stream.history
        messages = [ChatMessage(role="system", content=system_prompt)]
        for m in history:
            role = "assistant" if m.author_id.lower() == agent_name.lower() else "user"
            messages.append(ChatMessage(role=role, content=m.content))
        
        messages.append(ChatMessage(role="user", content=user_input))
        
        console.print(f"\n[bold cyan]{agent_name}:[/bold cyan] ", end="")
        
        full_response = ""
        try:
            # Stream response
            with Live(Text(""), refresh_per_second=10) as live:
                # Use complete_streaming from llm_client
                async for chunk in llm.complete_streaming(messages):
                    full_response += chunk
                    # Don't show [SILENCE] to user
                    if "[SILENCE]" not in full_response:
                        live.update(Text(full_response, style="cyan"))
                    else:
                        live.update(Text("[Spirit remains silent]", style="dim italic"))
            
            # If the response ended up being just silence, handle it
            if "[SILENCE]" in full_response:
                console.print("\n[dim italic]The Spirit chose not to respond to this stimulus.[/dim italic]")
                continue
                
        except Exception as e:
            console.print(f"[red]Inference Error: {e}[/red]")
            continue
            
        # 4. Prism Store (Deep Well & Fast Stream Response)
        await prism.add_chat_message(session_id, agent_name, full_response)
        
        # Periodic "Consolidation" (Self-directed thought storage)
        # Store the response as an episodic memory
        from src.core.memory.types import EpisodicMemory
        mem = EpisodicMemory(
            author_id=agent_name,
            content=f"I responded to a query regarding '{user_input[:20]}...'",
            subjective_voice=f"I communicated with the Lord. My response: {full_response[:50]}...",
            emotional_valence=0.0
        )
        await prism.store_memory(mem)
        print("\n")

import os
