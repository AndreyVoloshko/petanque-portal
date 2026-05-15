#!/usr/bin/env bash

. .env

export POSTGRES_PASSWORD=$(python3 -c "import json,os; print(json.loads(os.environ['APP_CREDENTIALS'])['db_pass'])")
export POSTGRES_USER=$(python3 -c "import json,os; print(json.loads(os.environ['APP_CREDENTIALS'])['db_user'])")
export POSTGRES_DB=$(python3 -c "import json,os; print(json.loads(os.environ['APP_CREDENTIALS'])['db_name'])")

docker compose -p "petanque-portal" up --build
