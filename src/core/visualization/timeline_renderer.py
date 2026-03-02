"""
VoidCat RDC: Sovereign Spirit - Timeline Renderer
==================================================
Version: 1.0.0
Author: Vivy (Context Integrator)
Date: 2026-02-28

Generates an HTML timeline report from Chronicler events.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Any

logger = logging.getLogger("sovereign.visualization.timeline")

_OUTPUT_DIR = Path("logs/timelines")


class TimelineRenderer:
    """Renders a list of TimelineEvents as a self-contained HTML report."""

    def __init__(self, output_dir: Path = _OUTPUT_DIR) -> None:
        self.output_dir = output_dir

    def generate_html_report(self, events: List[Any]) -> Path:
        """
        Generate an HTML timeline and write it to output_dir.

        Args:
            events: List of TimelineEvent objects from Chronicler.

        Returns:
            Path to the generated HTML file.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"timeline_{timestamp}.html"

        rows = ""
        for event in sorted(events, key=lambda e: e.timestamp, reverse=True):
            ts = event.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
            details_html = (
                f"<br><small style='color:#aaa'>{event.details}</small>"
                if event.details
                else ""
            )
            rows += (
                f"<tr>"
                f"<td>{ts}</td>"
                f"<td><b>{event.actor_name}</b></td>"
                f"<td><code>{event.event_type}</code></td>"
                f"<td>{event.summary}{details_html}</td>"
                f"</tr>\n"
            )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sovereign Spirit — Timeline</title>
<style>
  body {{ font-family: monospace; background: #0d0d0d; color: #e0e0e0; margin: 2rem; }}
  h1 {{ color: #c084fc; }}
  p.meta {{ color: #888; font-size: 0.85rem; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th {{ background: #1a1a2e; color: #c084fc; padding: 0.5rem 1rem; text-align: left; }}
  td {{ padding: 0.4rem 1rem; border-bottom: 1px solid #222; vertical-align: top; }}
  tr:hover td {{ background: #161630; }}
  code {{ color: #7dd3fc; }}
</style>
</head>
<body>
<h1>Sovereign Spirit — Event Timeline</h1>
<p class="meta">Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")} | Events: {len(events)}</p>
<table>
<thead><tr><th>Timestamp</th><th>Actor</th><th>Type</th><th>Summary</th></tr></thead>
<tbody>
{rows if rows else "<tr><td colspan='4' style='color:#666'>No events found.</td></tr>"}
</tbody>
</table>
</body>
</html>"""

        output_path.write_text(html, encoding="utf-8")
        logger.info(f"Timeline report written to {output_path}")
        return output_path
