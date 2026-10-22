#!/bin/bash
set -euo pipefail
APT_OPTS=(-o Acquire::Retries=3 -o Acquire::http::Timeout=15 -o Acquire::https::Timeout=15)
if ! sudo apt-get "${APT_OPTS[@]}" install -y love xvfb; then
  echo "install against cached metadata failed; refreshing the index" >&2
  sudo apt-get "${APT_OPTS[@]}" update
  sudo apt-get "${APT_OPTS[@]}" install -y love xvfb
fi
