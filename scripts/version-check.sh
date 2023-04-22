#!/bin/sh
#
# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

set -e

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)"
VERSION="${1}"

if [ ! -f "${SCRIPT_DIR}/../venv/bin/activate" ]; then
    echo "ERROR: Could not find virtual environment to use."
fi

cd "${SCRIPT_DIR}/../"

# shellcheck disable=SC1090,SC1091
. "${SCRIPT_DIR}/../venv/bin/activate"

case "${VERSION}" in
    dev|edge) exit 0 ;;
    '')
        echo "!!! No version passed to version check script."
        exit 1
        ;;
    *)
        if ! echo "${VERSION}" | grep -Eq "^v[0-9]+.[0-9]+.[0-9]+"; then
            echo "!!! ${VERSION} is not a properly formatted version number."
            exit 1
        fi

        pyversion="v$(python -c "import roll35; print(roll35.__version__)")"

        if [ "${VERSION}" != "${pyversion}" ]; then
            echo "!!! ${VERSION} does not match version in Python module (${pyversion})"
            exit 1
        fi
        ;;
esac
