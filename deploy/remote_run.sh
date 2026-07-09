#!/usr/bin/env bash

set -e

set -a
. .env
set +a

export POSTGRES_PASSWORD=$(python3 -c "import json,os; print(json.loads(os.environ['APP_CREDENTIALS'])['db_pass'])")
export POSTGRES_USER=$(python3 -c "import json,os; print(json.loads(os.environ['APP_CREDENTIALS'])['db_user'])")
export POSTGRES_DB=$(python3 -c "import json,os; print(json.loads(os.environ['APP_CREDENTIALS'])['db_name'])")

# Fider feedback board (feedback.petanque.org.ua) — reuses SMTP credentials
# from APP_CREDENTIALS; fider_jwt_secret must be added there once.
export FIDER_JWT_SECRET=$(python3 -c "import json,os; print(json.loads(os.environ['APP_CREDENTIALS']).get('fider_jwt_secret',''))")
export FIDER_SMTP_HOST=$(python3 -c "import json,os; print(json.loads(os.environ['APP_CREDENTIALS']).get('smtp_host',''))")
export FIDER_SMTP_PORT=$(python3 -c "import json,os; print(json.loads(os.environ['APP_CREDENTIALS']).get('smtp_port','587'))")
export FIDER_SMTP_USERNAME=$(python3 -c "import json,os; print(json.loads(os.environ['APP_CREDENTIALS']).get('smtp_user',''))")
export FIDER_SMTP_PASSWORD=$(python3 -c "import json,os; print(json.loads(os.environ['APP_CREDENTIALS']).get('smtp_password',''))")
export FIDER_EMAIL_NOREPLY=$(python3 -c "import json,os; c=json.loads(os.environ['APP_CREDENTIALS']); print(c.get('smtp_from_email') or c.get('smtp_from') or 'noreply@petanque.org.ua')")

docker compose -p "petanque-portal" --profile feedback build
docker compose -p "petanque-portal" run --rm --no-deps --entrypoint python petanque_portal_web_api manage.py collectstatic --noinput
docker compose -p "petanque-portal" --profile feedback up -d
