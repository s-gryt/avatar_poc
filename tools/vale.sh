#!/usr/bin/env sh
set -eu
[ -d .vale/styles/Google ] || vale sync >&2
alerts=$(vale --no-exit --output=line --minAlertLevel=suggestion "$@")
[ -z "$alerts" ] && exit 0
printf '%s\n' "$alerts"
exit 1
