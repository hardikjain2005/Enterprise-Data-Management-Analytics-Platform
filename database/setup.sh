#!/usr/bin/env bash
# ---------------------------------------------------------------------
# Builds (or rebuilds) the whole database from the SQL scripts.
# Reads connection details from the project's .env file.
#
#   ./database/setup.sh
#
# WARNING: schema.sql drops and recreates every table, so all data is
# deleted. Run the ETL afterwards to load the sample data again.
# ---------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing .env file. Copy .env.example to .env and fill in your values." >&2
  exit 1
fi

# Load KEY=VALUE pairs from .env
set -a
source "$ENV_FILE"
set +a

# MYSQL_PWD keeps the password off the command line (and out of `ps`).
export MYSQL_PWD="$DB_PASSWORD"
MYSQL=(mysql --host="$DB_HOST" --port="$DB_PORT" --user="$DB_USER" --database="$DB_NAME")

for file in schema.sql indexes.sql procedures.sql triggers.sql views.sql seed.sql; do
  echo "Running $file ..."
  "${MYSQL[@]}" < "$SCRIPT_DIR/$file"
done

echo "Database '$DB_NAME' is ready. Next step: python etl/scripts/run_pipeline.py"
