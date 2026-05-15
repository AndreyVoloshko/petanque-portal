#!/bin/sh
set -e
cron
exec /docker-entrypoint.sh "$@"
