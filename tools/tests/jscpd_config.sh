#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "$0")/../.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
passed=0
failed=0

expect() {
  local want=$1 name=$2
  if jscpd --config "$root/.jscpd.json" --silent "$work/$name" >"$work/$name.out" 2>&1; then got=pass; else got=fail; fi
  if [ "$got" = "$want" ]; then
    passed=$((passed + 1))
  else
    failed=$((failed + 1))
    printf 'FAIL %s: expected %s, got %s\n' "$name" "$want" "$got"
    sed 's/^/    /' "$work/$name.out"
  fi
}

mkdir -p "$work/distinct-tables" "$work/aligned-tables" "$work/repeated-row" "$work/repeated-block"

cat >"$work/distinct-tables/a.md" <<'EOF'
# Alpha

| Concept | Owner | Reason |
| --- | --- | --- |
| Session lifecycle | Domain | Business rule |
| Provider timeout | Contracts | Port behavior |
EOF

cat >"$work/distinct-tables/b.md" <<'EOF'
# Beta

| Slice | Trigger | Outcome |
| --- | --- | --- |
| Greeting | Visitor arrives | Avatar speaks |
| Farewell | Visitor leaves | Session closes |
EOF

cat >"$work/aligned-tables/a.md" <<'EOF'
# Alpha

| Metric | Target | Gate |
| :--- | :---: | ---: |
| First audio latency | 800 ms | Gate 1 |
EOF

cat >"$work/aligned-tables/b.md" <<'EOF'
# Beta

| Port | Adapter | Fallback |
| :--- | :---: | ---: |
| Speech synthesis | Cloud voice | Silence |
EOF

cat >"$work/repeated-row/a.md" <<'EOF'
# Alpha

| Concept | Owner | Reason |
| --- | --- | --- |
| Session lifecycle belongs to the domain | Domain | Business rule |
EOF

cat >"$work/repeated-row/b.md" <<'EOF'
# Beta

| Slice | Trigger | Outcome |
| --- | --- | --- |
| Session lifecycle belongs to the domain | Domain | Business rule |
EOF

cat >"$work/repeated-block/a.md" <<'EOF'
# Alpha

Ports return explicit outcomes.
Adapters translate provider errors.
The composition root wires every adapter.
EOF

cat >"$work/repeated-block/b.md" <<'EOF'
# Beta

Ports return explicit outcomes.
Adapters translate provider errors.
The composition root wires every adapter.
EOF

expect pass distinct-tables
expect pass aligned-tables
expect fail repeated-row
expect fail repeated-block

printf 'jscpd config: %d passed, %d failed\n' "$passed" "$failed"
[ "$failed" -eq 0 ]
