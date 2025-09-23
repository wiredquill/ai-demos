#!/usr/bin/env bash
#
# @file 5-Remove-unused-files.sh
# @brief Remove unused files from the chart and fix existing ones
# @description Remove all files that are not expected to be bundled with the
#   chart, in addition to fixing any files that may be improperly bundled.
#
# @noargs
#
# @env PACKAGE_PATH string Path to the package in the repository.
#
# @require sed

# Strict mode
set -euo pipefail

# Debug mode
# set -x

GIT_ROOT_PATH="$(git rev-parse --show-toplevel)"
source "$GIT_ROOT_PATH/scripts/functions.sh"

check_required_environment_variables PACKAGE_PATH

pushd "$GIT_ROOT_PATH/packages/$PACKAGE_PATH" &>/dev/null
rm -rf .asf.yml .git .github templates/tests tests artifacthub-repo.yml

popd &>/dev/null
