#!/usr/bin/env bash

set -e

FWDIR="$(cd "`dirname $0`"; pwd)"
cd "$FWDIR"

pylint mlflow
# prospector --profile "$FWDIR/prospector.yaml" -i "example"

rstcheck README.rst
