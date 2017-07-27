#!/bin/bash

set -e

bash bash/dev/compile_code.sh
docker-compose build
