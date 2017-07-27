#!/bin/bash

set -e

git submodule update --init --recursive --force
ftj -r dev