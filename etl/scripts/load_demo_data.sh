#!/usr/bin/env bash
# ---------------------------------------------------------------------
# Rebuilds the database and loads the full demo story in one command:
#   1. initial extract (with bad rows)      -> PARTIAL_SUCCESS runs
#   2. next-day delta (new + changed rows)  -> SUCCESS runs, UPDATE audit entries
#   3. broken customers file                -> one FAILED run
#
#   ./etl/scripts/load_demo_data.sh
# ---------------------------------------------------------------------
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"

"$ROOT/database/setup.sh"
"$PYTHON" "$ROOT/etl/scripts/run_pipeline.py" --data-dir "$ROOT/etl/data/raw"
"$PYTHON" "$ROOT/etl/scripts/run_pipeline.py" --data-dir "$ROOT/etl/data/incremental"
# This run is EXPECTED to fail (the file has no email column), so ignore its exit code.
"$PYTHON" "$ROOT/etl/scripts/run_pipeline.py" --data-dir "$ROOT/etl/data/bad_batch" \
    --jobs load_customers --skip-dq-checks || true

echo "Demo data loaded."
