#!/bin/sh
# Runs database migrations, then starts the app (the command passed to the container).
set -eu
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  echo "running migrations"
  alembic upgrade head
fi
exec "$@"
