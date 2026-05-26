#!/usr/bin/env bash

set -e

set -a
. .env
set +a

export POSTGRES_PASSWORD=$(python3 -c "import json,os; print(json.loads(os.environ['APP_CREDENTIALS'])['db_pass'])")
export POSTGRES_USER=$(python3 -c "import json,os; print(json.loads(os.environ['APP_CREDENTIALS'])['db_user'])")
export POSTGRES_DB=$(python3 -c "import json,os; print(json.loads(os.environ['APP_CREDENTIALS'])['db_name'])")

docker compose -p "petanque-portal" build
docker compose -p "petanque-portal" run --rm --no-deps --entrypoint python petanque_portal_web_api manage.py collectstatic --noinput
docker compose -p "petanque-portal" up -d
