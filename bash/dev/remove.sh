#!/bin/bash

set -e

bash bash/dev/stop.sh
docker-compose rm
