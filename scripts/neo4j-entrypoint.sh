#!/bin/bash
# Beatrice's Purification Protocol
# Prevents "Store Lock" errors by cleaning up before startup

set -e

echo "🔍 [Purification] Checking for stale Neo4j lock files..."

# Define the data directory (internal container path)
DATA_DIR="/data"

# List of lock files that cause boot loops
LOCK_FILES=(
    "$DATA_DIR/databases/store_lock"
    "$DATA_DIR/databases/system/store_lock"
    "$DATA_DIR/databases/neo4j/store_lock"
    "$DATA_DIR/neo4j.pid"
)

for lock_file in "${LOCK_FILES[@]}"; do
    if [ -f "$lock_file" ]; then
        echo "⚠️  [Purification] Found stale lock: $lock_file"
        rm -f "$lock_file"
        echo "✅ [Purification] Lock destroyed."
    fi
done

# Extra purification for the runtime PID file (the cause of the panic)
# Extra purification for the runtime PID file (the cause of the panic)
echo "🔍 [Purification] Hunting down ALL stale neo4j.pid files..."
find /var /data -name "neo4j.pid" -type f -exec rm -fv {} \;

echo "✨ [Purification] Complete. Handing control to Neo4j..."
# Execute the original Docker entrypoint
exec /startup/docker-entrypoint.sh neo4j
