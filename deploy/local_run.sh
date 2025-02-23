#!/usr/bin/env bash

. .env

docker compose -p "petanque-portal" up --build
