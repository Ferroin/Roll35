#!/bin/sh
#
# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)"

if [ ! -f "${SCRIPT_DIR}/../venv/bin/activate" ]; then
    echo "ERROR: Could not find virtual environment to use."
fi

cd "${SCRIPT_DIR}/" || exit 1

# shellcheck disable=SC1090,SC1091
. "${SCRIPT_DIR}/venv/bin/activate" || exit 1

exec python -m roll35
