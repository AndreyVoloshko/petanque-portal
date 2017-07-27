#!/bin/bash

set -e

# Compile code using ftj
bash bash/prod/actions/compile_code.sh

# Push new code if necessary
if [[ $1 == "push" ]]; then
   bash bash/prod/actions/push.sh
else
   echo "Push skipped! Use 'push' as 1st arg"
fi

# Activate default docker machine locally
. bash/prod/actions/machine_activate.sh

# Remove stack if required (sometimes errors with secrets occur which prevent deploying)
if [[ $2 == "stack_rm" ]]; then
   bash bash/prod/actions/stack_remove.sh
else
   echo "Stack remove skipped! Use 'stack_rm' as 2nd arg"
fi

# Deploy stack
bash bash/prod/actions/stack_deploy.sh

#clean up
bash bash/prod/actions/cleanup.sh