#!/usr/bin/env bash
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
passed=0
failed=0

expect() {
  local want=$1 name=$2
  shift 2
  if "$@" >"$work/out" 2>&1; then got=pass; else got=fail; fi
  if [ "$got" = "$want" ]; then
    passed=$((passed + 1))
  else
    failed=$((failed + 1))
    printf 'FAIL %s: expected %s, got %s\n' "$name" "$want" "$got"
    sed 's/^/    /' "$work/out"
  fi
}

cat >"$work/commit-good" <<'EOF'
ci(guardrails): run docs checks only on pull requests to main

Impact: Contributors get one docs-guardrails run per pull request
instead of two; direct pushes to branches no longer trigger it.
Why: Pushes to feature branches ran the full docs gate twice, once on
push and once on the pull request, doubling CI minutes.
Risk: high - a misconfigured trigger would let unchecked docs merge;
verified by opening a draft PR and seeing the check run.
EOF

cat >"$work/commit-narration" <<'EOF'
ci: update workflow

Impact: Updated docs-guardrails.yml to remove the push trigger line.
EOF

cat >"$work/commit-no-why" <<'EOF'
feat(agents): teach agents to describe impact in commits

Impact: Agents now explain who notices a change and how it was verified.
EOF

cat >"$work/commit-low-risk" <<'EOF'
docs: fix broken link to validation guide

Impact: Readers following the docs index reach the validation page.
EOF

cat >"$work/commit-underrated" <<'EOF'
ci: drop weekly schedule from docs checks

Impact: Docs checks stop running on Mondays; pull requests still run them.
Why: The weekly run duplicated pull request checks with no new signal.
Risk: low - schedule only.
EOF

cat >"$work/commit-why-first" <<'EOF2'
fix(docs): restore the validation guide link

Why: The docs index pointed at a renamed page.
Impact: Readers following the docs index reach the validation page.
EOF2

printf 'Fix: The bug.\n' >"$work/subject-bad"
printf 'feat(skills): add impact-recap for commit and PR descriptions\n' >"$work/subject-good"

cat >"$work/pr-good" <<'EOF'
<!-- impact-recap:start -->
## Impact

Agents writing commits or pull requests in this repo now lead with the
consequence of a change: who notices, what behaves differently, and how it
was verified. Reviewers can judge risk without reconstructing it from the diff.

## Why

Descriptions restated the diff, so reviewers re-derived intent and risk.

## Risk: medium

| Area | Risk | What changes in behavior |
| ---- | ---- | ------------------------ |
| Agent instructions | medium | Agents follow the new description shape |

Only agent instructions change; no gate or CI behavior moves.

## Flow

```mermaid
sequenceDiagram
  participant Agent
  participant Facts as facts.sh
  Agent->>Facts: collect diff facts
  Facts-->>Agent: areas and risk floor
```

## Verification

- scripts/test.sh passes
<!-- impact-recap:end -->
EOF

sed 's/^## Risk: medium$/## Risk: low/' "$work/pr-good" >"$work/pr-underrated"
sed 's/collect diff facts/collect; facts/' "$work/pr-good" >"$work/pr-semicolon"
grep -v 'impact-recap:end' "$work/pr-good" >"$work/pr-unterminated"
awk '/^## Verification/ { skip = 1 } /impact-recap:end/ { skip = 0 } !skip' "$work/pr-good" >"$work/pr-no-verification"
cat >"$work/pr-diff-dump" <<'EOF'
<!-- impact-recap:start -->
## Impact

Changed SKILL.md and lint.sh and facts.sh and areas.tsv and upsert-pr.sh and test.sh in the skill folder.

## Why

Needed.

## Risk: medium

Low.

## Verification

None yet.
<!-- impact-recap:end -->
EOF

expect pass commit-good "$here/lint.sh" commit "$work/commit-good" --risk high
expect fail commit-narration "$here/lint.sh" commit "$work/commit-narration"
expect fail commit-missing-why-at-medium "$here/lint.sh" commit "$work/commit-no-why" --risk medium
expect pass commit-low-needs-impact-only "$here/lint.sh" commit "$work/commit-low-risk" --risk low
expect fail commit-risk-below-facts "$here/lint.sh" commit "$work/commit-underrated" --risk high
expect fail commit-why-before-impact "$here/lint.sh" commit "$work/commit-why-first"
expect fail subject-not-conventional "$here/lint.sh" subject "$work/subject-bad"
expect pass subject-conventional "$here/lint.sh" subject "$work/subject-good"
awk -v filler="$(printf 'Reviewers notice one more consequence here. %.0s' $(seq 1 60))" '
  /^## Why/ { print filler; print "" } { print }
' "$work/pr-good" >"$work/pr-too-long"

expect pass pr-good "$here/lint.sh" pr "$work/pr-good" --risk medium
expect fail pr-over-word-limit "$here/lint.sh" pr "$work/pr-too-long" --risk medium
expect fail pr-risk-below-facts "$here/lint.sh" pr "$work/pr-underrated" --risk medium
expect fail pr-mermaid-semicolon "$here/lint.sh" pr "$work/pr-semicolon"
expect fail pr-unterminated "$here/lint.sh" pr "$work/pr-unterminated"
expect fail pr-no-verification "$here/lint.sh" pr "$work/pr-no-verification"
expect fail pr-diff-dump "$here/lint.sh" pr "$work/pr-diff-dump"

printf 'Hand-written intro.\n\n' >"$work/body-plain"
"$here/upsert-pr.sh" --merge "$work/body-plain" "$work/pr-good" >"$work/merged-once"
{ cat "$work/merged-once"; printf '\nSummary by CodeRabbit\n'; } >"$work/body-with-tail"
sed 's/Only agent instructions change/Agent instructions change/' "$work/pr-good" >"$work/pr-revised"
"$here/upsert-pr.sh" --merge "$work/body-with-tail" "$work/pr-revised" >"$work/merged-twice"

expect pass upsert-keeps-intro grep -qx 'Hand-written intro.' "$work/merged-once"
expect pass upsert-appends-block grep -qx '<!-- impact-recap:end -->' "$work/merged-once"
expect pass upsert-replaces-block grep -q '^Agent instructions change' "$work/merged-twice"
expect fail upsert-drops-old-block grep -q '^Only agent instructions change' "$work/merged-twice"
expect pass upsert-keeps-tail grep -qx 'Summary by CodeRabbit' "$work/merged-twice"
expect pass upsert-single-block test "$(grep -c 'impact-recap:start' "$work/merged-twice")" -eq 1

repo="$work/repo"
git init -q "$repo"
git_in_repo() { git -C "$repo" -c user.name=test -c user.email=test@example.invalid -c commit.gpgsign=false "$@"; }
facts_in_repo() { (cd "$repo" && "$here/facts.sh" "$@"); }
git_in_repo commit -q --allow-empty -m base
mkdir -p "$repo/.github/workflows"
printf 'on: pull_request\n' >"$repo/.github/workflows/check.yml"
git_in_repo add .github
git_in_repo commit -q -m ci

facts_in_repo --base HEAD~1 --head HEAD >"$work/facts" 2>/dev/null
expect pass facts-rates-ci-high grep -q '^risk: high (driven by ci)' "$work/facts"
expect fail facts-empty-scope facts_in_repo --base HEAD --head HEAD
printf 'draft\n' >"$repo/notes.md"
git_in_repo add notes.md
facts_in_repo --staged >"$work/facts-staged" 2>/dev/null
expect pass facts-staged-rates-docs-low grep -q '^risk: low (driven by docs)' "$work/facts-staged"

cat >"$work/commit-risk-before-why" <<'EOF2'
fix(docs): restore the validation guide link

Impact: Readers following the docs index reach the validation page.
Risk: low - one link target.
Why: The docs index pointed at a renamed page.
EOF2
expect fail commit-why-after-risk "$here/lint.sh" commit "$work/commit-risk-before-why"
expect fail facts-staged-with-range "$here/facts.sh" --staged --base HEAD

grep -v '^| Agent instructions' "$work/pr-good" >"$work/pr-no-risk-row"
awk '/^\| Area/ { next } { print } /^\| Agent instructions/ { print }' "$work/pr-good" >"$work/pr-no-risk-header"
sed 's/^| Agent instructions.*$/| unspecified |/' "$work/pr-good" >"$work/pr-one-cell-risk-row"
sed 's/^| Agent instructions.*$/|   | medium | Agents follow the new description shape |/' "$work/pr-good" >"$work/pr-empty-risk-area"
sed 's/^| Agent instructions.*$/| Agent instructions |   | Agents follow the new description shape |/' "$work/pr-good" >"$work/pr-empty-risk-level"
sed 's/^| Agent instructions.*$/| Agent instructions | medium |   |/' "$work/pr-good" >"$work/pr-empty-risk-consequence"
sed 's/^- scripts\/test.sh passes$/scripts\/test.sh passes/' "$work/pr-good" >"$work/pr-no-verification-item"
expect fail pr-risk-without-area-row "$here/lint.sh" pr "$work/pr-no-risk-row"
expect fail pr-risk-without-header "$here/lint.sh" pr "$work/pr-no-risk-header"
expect fail pr-one-cell-risk-row "$here/lint.sh" pr "$work/pr-one-cell-risk-row"
expect fail pr-empty-risk-area "$here/lint.sh" pr "$work/pr-empty-risk-area"
expect fail pr-empty-risk-level "$here/lint.sh" pr "$work/pr-empty-risk-level"
expect fail pr-empty-risk-consequence "$here/lint.sh" pr "$work/pr-empty-risk-consequence"
expect fail pr-verification-without-item "$here/lint.sh" pr "$work/pr-no-verification-item"

write_commit() {
  printf 'docs(guide): restore the validation guide link\n\nImpact: %s\n' "$2" >"$work/$1"
}
write_commit commit-editors 'Editors of the docs index reach the validation page again.'
write_commit commit-replaced 'Replaced the trigger so contributors get one check per PR.'
write_commit commit-node 'Contributors on Node.js 20 run the docs gate without errors.'
write_commit commit-requirements 'Contributors installing requirements.txt get the pinned linter.'
printf 'docs(guide): restore the validation guide link\n\nImpact: Readers following the index reach\nNote: the validation page again after the rename.\n' >"$work/commit-note-continuation"

expect pass commit-noun-opener-is-not-edit-verb "$here/lint.sh" commit "$work/commit-editors"
expect fail commit-replaced-opener "$here/lint.sh" commit "$work/commit-replaced"
expect pass commit-framework-name-is-not-file "$here/lint.sh" commit "$work/commit-node"
expect fail commit-txt-file-named "$here/lint.sh" commit "$work/commit-requirements"
expect pass commit-colon-continuation "$here/lint.sh" commit "$work/commit-note-continuation"

awk '
  /^## Why/ { mode = "why" } /^## Risk/ { mode = "risk" } /^## Flow/ { mode = "" }
  mode == "why" { why = why $0 "\n"; next }
  mode == "risk" { risk = risk $0 "\n"; next }
  /^## Flow/ { printf "%s%s", risk, why }
  { print }
' "$work/pr-good" >"$work/pr-out-of-order"
awk '/^## Verification/ { print "## Before / after"; print ""; print "```markdown"; print "## Not a section"; print "```"; print "" } { print }' "$work/pr-good" >"$work/pr-heading-in-code"
expect fail pr-sections-out-of-order "$here/lint.sh" pr "$work/pr-out-of-order"
expect pass pr-heading-inside-code-fence "$here/lint.sh" pr "$work/pr-heading-in-code" --risk medium

printf 'intro\r\n<!-- impact-recap:start -->\r\nOLD\r\n<!-- impact-recap:end -->\r\nfooter\r\n' >"$work/body-crlf"
"$here/upsert-pr.sh" --merge "$work/body-crlf" "$work/pr-good" >"$work/merged-crlf"
expect fail upsert-crlf-drops-old-block grep -qx 'OLD' "$work/merged-crlf"
expect pass upsert-crlf-single-block test "$(grep -c 'impact-recap:start' "$work/merged-crlf")" -eq 1
expect pass upsert-crlf-keeps-footer grep -qx 'footer' "$work/merged-crlf"

printf 'a\n<!-- impact-recap:start -->\nuser text\n' >"$work/body-unclosed"
printf '<!-- impact-recap:end -->\ny\n<!-- impact-recap:start -->\nz\n' >"$work/body-reversed"
{ cat "$work/merged-once"; cat "$work/pr-good"; } >"$work/body-two-blocks"
expect fail upsert-refuses-unclosed "$here/upsert-pr.sh" --merge "$work/body-unclosed" "$work/pr-good"
expect fail upsert-refuses-reversed "$here/upsert-pr.sh" --merge "$work/body-reversed" "$work/pr-good"
expect fail upsert-refuses-two-blocks "$here/upsert-pr.sh" --merge "$work/body-two-blocks" "$work/pr-good"
expect fail upsert-refuses-missing-block "$here/upsert-pr.sh" --merge "$work/body-plain" "$work/missing"

root=$(git -C "$here" rev-parse --show-toplevel)
mapped="$work/mapped"
git init -q "$mapped"
git_in_mapped() { git -C "$mapped" -c user.name=test -c user.email=test@example.invalid -c commit.gpgsign=false "$@"; }
git_in_mapped commit -q --allow-empty -m base
git -C "$root" ls-files | awk '!/\//' >"$work/root-files"
git -C "$root" ls-files tools rules .vale .github .agents/skills/impact-recap/scripts >"$work/gate-files"
git -C "$root" ls-files | while IFS= read -r path; do
  grep -qF -- "$path" "$root/.pre-commit-config.yaml" "$root"/.github/workflows/*.yml 2>/dev/null && printf '%s\n' "$path"
done >>"$work/gate-files"
printf '.pre-commit-config.yaml\n' >>"$work/gate-files"
sort -u "$work/root-files" "$work/gate-files" | while IFS= read -r path; do
  mkdir -p "$mapped/$(dirname "$path")"
  printf 'x\n' >"$mapped/$path"
done
git_in_mapped add -A
git_in_mapped commit -q -m mapped
(cd "$mapped" && "$here/facts.sh" --base HEAD~1 --head HEAD --no-log) >"$work/mapped-facts" 2>/dev/null
awk '/^changes:/ { on = 1; next } on { print $2 "\t" $3 "\t" $4 }' "$work/mapped-facts" >"$work/mapped-rows"
expect pass areas-root-files-explicitly-mapped awk -F'\t' '
  FILENAME == ARGV[1] { root[$1] = 1; next }
  ($3 in root) && $1 == "source" { print "unmapped root file: " $3; bad = 1 }
  END { exit bad }
' "$work/root-files" "$work/mapped-rows"
expect pass areas-gate-files-rate-high awk -F'\t' '
  FILENAME == ARGV[1] { gate[$1] = 1; next }
  ($3 in gate) && $2 != "high" { print "gate file below high: " $3 " (" $1 " " $2 ")"; bad = 1 }
  END { exit bad }
' "$work/gate-files" "$work/mapped-rows"
expect pass areas-rates-every-expected-file awk -F'\t' '
  FILENAME == ARGV[1] { rated[$3] = 1; next }
  !($1 in rated) { print "not rated by facts.sh: " $1; bad = 1 }
  END { exit bad }
' "$work/mapped-rows" "$work/root-files" "$work/gate-files"

printf '%d passed, %d failed\n' "$passed" "$failed"
[ "$failed" -eq 0 ]
