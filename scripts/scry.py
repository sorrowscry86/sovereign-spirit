
import os
import time
import asyncio
import signal
import sys
import psycopg2
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from datetime import datetime
from dotenv import load_dotenv

# Load env
load_dotenv()

# Configuration
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_NAME = os.getenv("POSTGRES_DB", "voidcat_rdc")
DB_USER = os.getenv("POSTGRES_USER", "voidcat")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "voidcat_sovereign")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

console = Console()

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        return None

def fetch_logs(limit=10):
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT timestamp, agent_id, action, details 
            FROM heartbeat_logs 
            ORDER BY timestamp DESC 
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as e:
        return []

def make_layout():
    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=3)
    )
    return layout

def generate_table(rows):
    table = Table(title="Neural Activity Log", expand=True, border_style="cyan")
    table.add_column("Time", style="dim")
    table.add_column("Agent", style="magenta")
    table.add_column("Action", style="green")
    table.add_column("Details", style="white")

    for row in rows:
        ts = row[0].strftime("%H:%M:%S")
        agent = row[1]
        action = row[2]
        # Truncate details
        details = str(row[3])
        if len(details) > 80:
            details = details[:77] + "..."
        
        # Colorize ACT vs IDLE
        if action == "ACT":
            action = "[bold red]ACT[/]"
        elif action == "IDLE":
            action = "[dim]IDLE[/]"
            
        table.add_row(ts, agent, action, details)
        
    return table

def run_dashboard():
    layout = make_layout()
    layout["header"].update(Panel("[bold white]VOIDCAT SOVEREIGN MONITOR[/]", style="bold blue"))
    layout["footer"].update(Panel(f"Connected to: {DB_HOST}:{DB_PORT} | DB: {DB_NAME}", style="dim"))

    with Live(layout, refresh_per_second=1, screen=True) as live:
        try:
            while True:
                rows = fetch_logs(15)
                table = generate_table(rows)
                layout["main"].update(table)
                time.sleep(1)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    # Check dependencies
    try:
        import rich
        import psycopg2
    except ImportError:
        print("Please run: pip install rich psycopg2-binary")
        sys.exit(1)
        
    run_dashboard()
