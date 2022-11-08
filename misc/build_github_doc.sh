#!/bin/sh

PROJECT_ROOT=$(dirname $(dirname $(readlink -f $0)))

cd "$PROJECT_ROOT/doc"

make github
