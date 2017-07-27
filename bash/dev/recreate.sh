#!/bin/bash

set -e

bash bash/dev/compile_code.sh
bash bash/dev/stop.sh
bash bash/dev/remove.sh
bash bash/dev/build.sh
bash bash/dev/run.sh
