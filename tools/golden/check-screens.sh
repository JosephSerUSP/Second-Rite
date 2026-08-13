#!/bin/bash
set -u
cd "$(dirname "$0")/../.."
TEMP_OUT=$(mktemp)
TEMP_WIDE=$(mktemp)
FAILURES=()
trap 'rm -f "$TEMP_OUT" "$TEMP_WIDE"' EXIT

if xvfb-run -a love . screenshots > "$TEMP_OUT" && \
   python3 tools/golden/screens.py check --input "$TEMP_OUT"; then
    echo "[G5] classic: PASS"
else
    FAILURES+=(classic)
    echo "[G5] classic: FAIL"
fi

if xvfb-run -a love . surface-crop-check; then
    echo "[G5] crop invariant: PASS"
else
    FAILURES+=("crop invariant")
    echo "[G5] crop invariant: FAIL"
fi

if xvfb-run -a love . surface=wide screenshots > "$TEMP_WIDE" && \
   python3 tools/golden/screens.py check --input "$TEMP_WIDE" --surface wide; then
    echo "[G5] wide: PASS"
else
    FAILURES+=(wide)
    echo "[G5] wide: FAIL"
fi

if ((${#FAILURES[@]})); then
    echo "G5 failed: ${FAILURES[*]}" >&2
    exit 1
fi
echo "SCREENS OK"
