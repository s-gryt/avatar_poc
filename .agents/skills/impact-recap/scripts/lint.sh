#!/usr/bin/env bash
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)

usage() {
  printf 'usage: %s subject|commit|pr <file> [--risk none|low|medium|high]\n' "${0##*/}" >&2
  exit 2
}

[ $# -ge 2 ] || usage
kind=$1
file=$2
shift 2
case $kind in subject|commit|pr) ;; *) usage ;; esac

floor=""
while [ $# -gt 0 ]; do
  case $1 in
    --risk) [ $# -ge 2 ] || usage; floor=$2; shift 2 ;;
    *) usage ;;
  esac
done
case $floor in ""|none) floor="" ;; low|medium|high) ;; *) usage ;; esac

[ -r "$file" ] || { printf 'lint.sh: cannot read %s\n' "$file" >&2; exit 2; }

if LC_ALL=C awk -v kind="$kind" -v floor="$floor" -f "$here/lint.awk" "$file"; then
  printf 'lint.sh: %s ok\n' "$kind"
else
  exit 1
fi
