"""
VoidCat RDC: Sovereign Spirit - Timeline Renderer
=================================================
Author: Echo (E-01)
Date: 2026-01-24

Renders Chronicler event streams into visual HTML artifacts using Mermaid.js.
"""

import os
from datetime import datetime
from typing import List
from pathlib import Path

from src.core.chronicler import TimelineEvent

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Sovereign Spirit: Chronicles</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #0d1117;
            color: #c9d1d9;
            margin: 20px;
        }}
        h1 {{ color: #58a6ff; text-align: center; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .mermaid {{ background: #161b22; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .log-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        .log-table th, .log-table td {{ border: 1px solid #30363d; padding: 8px; text-align: left; }}
        .log-table th {{ background-color: #161b22; color: #58a6ff; }}
        .log-table tr:nth-child(even) {{ background-color: #161b22; }}
        .timestamp {{ color: #8b949e; font-size: 0.9em; }}
        .actor {{ font-weight: bold; color: #79c0ff; }}
        .type {{ font-size: 0.8em; padding: 2px 6px; border-radius: 4px; }}
        .type-HEARTBEAT {{ background-color: #238636; color: white; }}
        .type-MESSAGE_SENT {{ background-color: #1f6feb; color: white; }}
    </style>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
    </script>
</head>
<body>
    <div class="container">
        <h1>The Chronicles of the Sovereign Spirit</h1>
        <p style="text-align: center; color: #8b949e;">Generated: {generated_at}</p>
        
        <div class="mermaid">
            gantt
            title Pantheon Activity Timeline
            dateFormat YYYY-MM-DD HH:mm:ss
            axisFormat %H:%M
            
            {gantt_content}
        </div>

        <h2>Event Log stream</h2>
        <table class="log-table">
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Actor</th>
                    <th>Type</th>
                    <th>Summary</th>
                    <th>Details</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

class TimelineRenderer:
    """Renders timelines to HTML."""

    def generate_html_report(self, events: List[TimelineEvent], output_path: str = "chronicles.html") -> str:
        """
        Generate a comprehensive HTML report with Mermaid Gantt chart.
        """
        # 1. Build Gantt Content
        # Mermaid Gantt syntax:
        # section ActorName
        # TaskName : [active, ] start_time, duration/end_time
        
        # We need to group events by Actor
        actors = {}
        sorted_events = sorted(events, key=lambda x: x.timestamp) # Oldest first for gantt
        
        for e in sorted_events:
            if e.actor_name not in actors:
                actors[e.actor_name] = []
            actors[e.actor_name].append(e)
            
        gantt_lines = []
        for actor, actor_events in actors.items():
            gantt_lines.append(f"section {actor}")
            for e in actor_events:
                # Format: 2026-01-24 14:30:00
                ts_str = e.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                # We give short duration for point events (1m)
                # Escape summary for mermaid safety
                safe_summary = e.summary.replace(":", "-").replace("#", "")
                
                # Different styling based on type?
                # crit for errors? active for messages?
                modifier = ""
                if e.event_type == "MESSAGE_SENT":
                    modifier = "active,"
                elif "ERROR" in safe_summary.upper():
                    modifier = "crit,"
                    
                gantt_lines.append(f"{safe_summary} :{modifier} {ts_str}, 1m")

        gantt_content = "\n            ".join(gantt_lines)

        # 2. Build Table Rows
        # Newest first for log table (which matches default get_timeline sort)
        table_rows = []
        for e in events: # events were passed in generic order, chronicler usually returns newest first
            ts_display = e.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            type_class = f"type-{e.event_type}"
            row = f"""
            <tr>
                <td class="timestamp">{ts_display}</td>
                <td class="actor">{e.actor_name}</td>
                <td><span class="type {type_class}">{e.event_type}</span></td>
                <td>{e.summary}</td>
                <td>{e.details or ''}</td>
            </tr>
            """
            table_rows.append(row)

        # 3. Fill Template
        html = HTML_TEMPLATE.format(
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            gantt_content=gantt_content,
            table_rows="\n".join(table_rows)
        )

        # 4. Write to File
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
            
        return os.path.abspath(output_path)
