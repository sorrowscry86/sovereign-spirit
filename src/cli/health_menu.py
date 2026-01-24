"""
VoidCat RDC: Sovereign Spirit - Health Menu
============================================
System health and status checks.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.core.database import get_database
from src.core.graph import get_graph
from src.core.llm_client import get_llm_client


async def show_health_menu(console: Console) -> None:
    """Display system health status."""
    console.clear()
    console.print(Panel("[bold cyan]System Health[/bold cyan]", border_style="blue"))
    
    # Create status table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan", width=20)
    table.add_column("Status", style="green", width=15)
    table.add_column("Details", style="dim")
    
    # Check PostgreSQL
    pg_status, pg_details = await check_postgres()
    table.add_row("PostgreSQL", pg_status, pg_details)
    
    # Check Neo4j
    neo_status, neo_details = await check_neo4j()
    table.add_row("Neo4j", neo_status, neo_details)
    
    # Check LLM
    llm_status, llm_details = await check_llm()
    table.add_row("LLM Provider", llm_status, llm_details)
    
    # Check Redis (if configured)
    redis_status, redis_details = await check_redis()
    table.add_row("Redis", redis_status, redis_details)
    
    # Check Weaviate (if configured)
    weaviate_status, weaviate_details = await check_weaviate()
    table.add_row("Weaviate", weaviate_status, weaviate_details)
    
    console.print(table)
    
    # Summary
    all_ok = all(s == "[green]● Online[/green]" for s, _ in [
        (pg_status, pg_details),
        (neo_status, neo_details),
        (llm_status, llm_details),
    ])
    
    if all_ok:
        console.print("\n[bold green]✓ All core systems operational[/bold green]")
    else:
        console.print("\n[bold yellow]⚠ Some systems may need attention[/bold yellow]")


async def check_postgres() -> tuple:
    """Check PostgreSQL connection."""
    try:
        db = get_database()
        if not db._initialized:
            await db.initialize()
        return "[green]● Online[/green]", "Connection verified"
    except Exception as e:
        # Fallback for host execution
        error_msg = str(e).lower()
        if "getaddrinfo failed" in error_msg or "could not translate host name" in error_msg:
            try:
                # Try localhost fallback manually
                from src.core.database import DatabaseClient, DATABASE_URL
                local_url = DATABASE_URL.replace("@postgres:", "@localhost:")
                local_db = DatabaseClient(database_url=local_url)
                await local_db.initialize()
                await local_db.close()
                return "[green]● Online[/green]", "Connection (via localhost)"
            except Exception:
                pass
        return "[red]● Offline[/red]", str(e)[:40]


async def check_neo4j() -> tuple:
    """Check Neo4j connection."""
    try:
        graph = get_graph()
        if not graph._initialized:
            await graph.initialize()
        is_healthy = await graph.health_check()
        if is_healthy:
            return "[green]● Online[/green]", "Connection verified"
        return "[yellow]● Degraded[/yellow]", "Health check failed"
    except Exception as e:
        # Fallback for host execution
        error_msg = str(e).lower()
        if "getaddrinfo failed" in error_msg or "failed to dns resolve" in error_msg or "serviceunavailable" in error_msg:
            try:
                # Try localhost fallback with explicit BOLT scheme
                from src.core.graph import GraphClient, NEO4J_USER, NEO4J_PASSWORD
                # Force bolt:// scheme for localhost to avoid routing issues
                local_uri = "bolt://localhost:7687"
                local_graph = GraphClient(uri=local_uri, user=NEO4J_USER, password=NEO4J_PASSWORD)
                await local_graph.initialize()
                is_healthy = await local_graph.health_check()
                await local_graph.close()
                if is_healthy:
                    return "[green]● Online[/green]", "Connection (via localhost)"
            except Exception as fallback_e:
                # Return the fallback error if that fails too
                return "[red]● Offline[/red]", f"Fallback failed: {str(fallback_e)[:30]}"
        return "[red]● Offline[/red]", str(e)[:40]


async def check_llm() -> tuple:
    """Check LLM provider connection."""
    try:
        client = get_llm_client()
        is_available = await client.health_check()
        if is_available:
            return "[green]● Online[/green]", f"Provider: {client.active_provider}"
        return "[yellow]● Degraded[/yellow]", "Provider not responding"
    except Exception as e:
        return "[red]● Offline[/red]", str(e)[:40]


async def check_redis() -> tuple:
    """Check Redis connection."""
    try:
        import redis.asyncio as redis
        # Try Docker hostname first
        try:
            r = await redis.from_url("redis://redis:6379", socket_timeout=2.0)
            await r.ping()
            await r.aclose()
            return "[green]● Online[/green]", "Connection verified"
        except Exception:
            # Fallback to localhost
            r = await redis.from_url("redis://localhost:6379", socket_timeout=2.0)
            await r.ping()
            await r.aclose()
            return "[green]● Online[/green]", "Connection (via localhost)"
    except ImportError:
        return "[dim]○ N/A[/dim]", "redis package not installed"
    except Exception as e:
        return "[yellow]● Not Connected[/yellow]", str(e)[:30]


async def check_weaviate() -> tuple:
    """Check Weaviate connection."""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("http://weaviate:8080/v1/.well-known/ready", timeout=5.0)
            if response.status_code == 200:
                return "[green]● Online[/green]", "Connection verified"
            return "[yellow]● Degraded[/yellow]", f"Status: {response.status_code}"
    except Exception as e:
        # Fallback for host execution
        if "getaddrinfo failed" in str(e).lower():
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    # Check port 8090 (mapped version)
                    response = await client.get("http://localhost:8090/v1/.well-known/ready", timeout=2.0)
                    if response.status_code == 200:
                        return "[green]● Online[/green]", "Connection (via localhost:8090)"
            except Exception:
                pass
        return "[yellow]● Not Connected[/yellow]", str(e)[:30]
