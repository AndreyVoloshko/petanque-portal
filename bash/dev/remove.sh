#!/bin/bash

set -e

bash bash/dev/stop.sh
docker-compose rm

#docker rmi $(docker images -f "dangling=true" -q)