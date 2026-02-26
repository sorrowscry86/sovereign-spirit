"""
Watchdog — Legacy Local Dev Server
===================================
Runs the Sovereign Spirit middleware outside Docker for local development.
For production, use `docker compose up` with the root docker-compose.yml.

Note: This is a simple wrapper. For full autonomy (heartbeat, stasis,
resurrection), use the Docker stack which includes all services.
"""

import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger("watchdog")

MIDDLEWARE_PORT = 8090


def run_server():
    logger.info("Initiating local middleware server...")
    cmd = [
        sys.executable, "-m", "uvicorn",
        "src.main:app",
        "--host", "0.0.0.0",
        "--port", str(MIDDLEWARE_PORT),
    ]

    try:
        process = subprocess.Popen(cmd)
        process.wait()

        if process.returncode != 0:
            logger.error(f"Server exited with code {process.returncode}. Auto-restart aborted.")
            sys.exit(process.returncode)
        else:
            logger.info("Server exited cleanly.")
    except KeyboardInterrupt:
        logger.info("Shutdown signal received.")
        process.terminate()
    except Exception as e:
        logger.error(f"Watchdog encountered failure: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_server()
