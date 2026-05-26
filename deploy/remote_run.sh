#!/usr/bin/env bash

. .env

docker compose -p "petanque-portal" build
docker compose -p "petanque-portal" run --rm --no-deps --entrypoint python petanque_portal_web_api manage.py collectstatic --noinput
docker compose -p "petanque-portal" up -d
