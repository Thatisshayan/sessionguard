#!/usr/bin/env bash
# seed_db.sh — Re-seed the database with fresh demo data (Mac/Linux).
# WARNING: Deletes all existing data.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "[SessionGuard] Re-seeding database with demo data..."
echo "WARNING: This will DELETE all existing data."
read -rp "Type YES to continue: " CONFIRM

if [ "$CONFIRM" != "YES" ]; then
    echo "Cancelled."
    exit 0
fi

python3 -c "from database.db import init_db, seed_demo_data; init_db(); seed_demo_data(force=True)"
echo "[SessionGuard] Database seeded successfully."
