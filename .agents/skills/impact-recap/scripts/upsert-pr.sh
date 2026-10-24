#!/usr/bin/env bash
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
start='<!-- impact-recap:start -->'
end='<!-- impact-recap:end -->'

usage() {
  printf 'usage: %s <pr-number> <block-file> [--risk <floor>] [--dry-run]\n' "${0##*/}" >&2
  printf '       %s --merge <body-file> <block-file>\n' "${0##*/}" >&2
  exit 2
}

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

marker_state() {
  awk -v start="$start" -v end="$end" '
    { line = $0; sub(/[ \t]+$/, "", line) }
    line == start { starts++; if (!start_at) start_at = NR }
    line == end { ends++; if (!end_at) end_at = NR }
    END {
      if (!starts && !ends) print "none"
      else if (starts == 1 && ends == 1 && start_at < end_at) print "one"
      else print "malformed"
    }
  ' "$1"
}

merge() {
  local body=$1 block=$2
  [ -r "$body" ] || { printf 'upsert-pr.sh: cannot read %s\n' "$body" >&2; return 2; }
  [ -r "$block" ] || { printf 'upsert-pr.sh: cannot read %s\n' "$block" >&2; return 2; }
  tr -d '\r' <"$body" >"$work/body.lf"
  tr -d '\r' <"$block" >"$work/block.lf"
  case $(marker_state "$work/body.lf") in
    none)
      awk 'NF { last = NR } { lines[NR] = $0 } END { for (i = 1; i <= last; i++) print lines[i]; if (last) print "" }' "$work/body.lf"
      cat "$work/block.lf"
      ;;
    one)
      awk -v start="$start" -v end="$end" -v block="$work/block.lf" '
        { line = $0; sub(/[ \t]+$/, "", line) }
        line == start { while ((getline replacement < block) > 0) print replacement; skipping = 1; next }
        skipping { if (line == end) skipping = 0; next }
        { print }
      ' "$work/body.lf"
      ;;
    *)
      printf 'upsert-pr.sh: PR body has unpaired, repeated, or out-of-order impact-recap markers; fix the body by hand, nothing was written\n' >&2
      return 1
      ;;
  esac
}

[ $# -ge 1 ] || usage

if [ "$1" = --merge ]; then
  [ $# -eq 3 ] || usage
  merge "$2" "$3"
  exit 0
fi

[ $# -ge 2 ] || usage
pr=$1
block=$2
shift 2
dry_run=0
risk=none
while [ $# -gt 0 ]; do
  case $1 in
    --dry-run) dry_run=1; shift ;;
    --risk) [ $# -ge 2 ] || usage; risk=$2; shift 2 ;;
    *) usage ;;
  esac
done

"$here/lint.sh" pr "$block" --risk "$risk" >&2

gh pr view "$pr" --json body --jq .body >"$work/body"
merge "$work/body" "$block" >"$work/next"

if [ "$dry_run" -eq 1 ]; then
  cat "$work/next"
elif cmp -s "$work/body.lf" "$work/next"; then
  printf 'upsert-pr.sh: PR #%s already current\n' "$pr" >&2
else
  gh pr view "$pr" --json body --jq .body >"$work/body.now"
  if ! cmp -s "$work/body" "$work/body.now"; then
    printf 'upsert-pr.sh: PR #%s body changed while merging; nothing was written, run again\n' "$pr" >&2
    exit 1
  fi
  gh pr edit "$pr" --body-file "$work/next" >/dev/null
  printf 'upsert-pr.sh: PR #%s recap updated\n' "$pr" >&2
fi
