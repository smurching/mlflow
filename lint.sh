#!/usr/bin/env bash

set -e

FWDIR="$(cd "`dirname $0`"; pwd)"
cd "$FWDIR"

# pylint mlflow --rcfile "$FWDIR/pylintrc"
prospector --profile "$FWDIR/prospector.yaml" -i "example" --show-profile --include-tool-stdout

rstcheck README.rst
