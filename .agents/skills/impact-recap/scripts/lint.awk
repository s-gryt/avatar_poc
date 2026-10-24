function rank(level) { return level == "high" ? 3 : level == "medium" ? 2 : level == "low" ? 1 : 0 }
function fail(message) { printf "%s: %s\n", FILENAME, message; failures++ }
function trim(text) { gsub(/^[ \t]+|[ \t]+$/, "", text); return text }
function words(text,    parts) { return split(trim(text), parts, /[ \t]+/) }
function bare(token) { gsub(/^[(\[`"']+|[)\]`"',.;:!?]+$/, "", token); return token }

function check_subject(subject) {
  if (subject !~ /^(feat|fix|docs|ci|build|chore|refactor|perf|test|style|revert)(\([a-z0-9._\/-]+\))?!?: [^ ]/)
    fail("subject must be '<type>(<scope>): <outcome>' with a conventional type and lowercase scope")
  if (length(subject) > 72) fail("subject is " length(subject) " bytes; limit is 72")
  if (subject ~ /\.$/) fail("subject must not end with a period")
}

function file_token(text,    tokens, count, i, token) {
  count = split(text, tokens, /[ \t]+/)
  for (i = 1; i <= count; i++) {
    token = bare(tokens[i])
    if (token ~ /^[A-Z][A-Za-z]*\.js$/) continue
    if (token ~ /\.(sh|bash|py|ts|tsx|js|mjs|cjs|jsx|yml|yaml|json|toml|md|mdx|tsv|csv|awk|txt|lock|cfg|ini|sql|html|css|go|rs|rb|java|kt|swift|env)$/) return token
    if (token ~ /^(Dockerfile|Makefile|Justfile)$/) return token
  }
  return ""
}

function check_impact(label, text,    opener, named) {
  text = trim(text)
  if (text == "") { fail(label " is missing or empty"); return }
  if (words(text) < minimum_words) fail(label " has " words(text) " words; write at least " minimum_words " about the consequence")
  opener = tolower(bare(substr(text, 1, index(text " ", " ") - 1)))
  if (opener in edit_verbs) fail(label " opens with an edit verb (" opener "); open with who or what is affected")
  named = file_token(text)
  if (named != "") fail(label " names a file (" named "); files are diff, impact is behavior")
}

function check_level(label, text,    level) {
  level = tolower(trim(text))
  sub(/[^a-z].*/, "", level)
  if (rank(level) == 0) { fail(label " must start with low, medium, or high"); return }
  if (rank(level) < rank(floor)) fail(label " is " level " but facts.sh rates the change " floor "; never rate below the facts")
}

BEGIN {
  failures = 0
  minimum_words = kind == "pr" ? 20 : 8
  start_marker = "<!-- impact-recap:start -->"
  end_marker = "<!-- impact-recap:end -->"
  verb_count = split("add adds added adding update updates updated updating change changes changed changing " \
    "modify modifies modified modifying edit edits edited editing bump bumps bumped bumping " \
    "touch touches touched touching tweak tweaks tweaked tweaking refactor refactors refactored refactoring " \
    "remove removes removed removing rename renames renamed renaming move moves moved moving " \
    "delete deletes deleted deleting create creates created creating introduce introduces introduced introducing " \
    "replace replaces replaced replacing implement implements implemented implementing " \
    "fix fixes fixed fixing drop drops dropped dropping enable enables enabled enabling " \
    "disable disables disabled disabling switch switches switched switching migrate migrates migrated migrating " \
    "convert converts converted converting extract extracts extracted extracting " \
    "rewrite rewrites rewrote rewritten rewriting adjust adjusts adjusted adjusting " \
    "improve improves improved improving enhance enhances enhanced enhancing", verb_list, " ")
  for (i = 1; i <= verb_count; i++) edit_verbs[verb_list[i]] = 1
}

{ sub(/\r$/, ""); lines[++count] = $0 }

END {
  if (count == 0) { fail("file is empty"); exit 1 }

  if (kind == "subject") { check_subject(lines[1]); exit (failures > 0) }

  if (kind == "commit") {
    check_subject(lines[1])
    if (count > 1 && lines[2] != "") fail("line 2 must be blank")
    current = ""
    for (i = 2; i <= count; i++) {
      if (length(lines[i]) > 72 && lines[i] !~ /https?:\/\//) fail("line " i " is " length(lines[i]) " bytes; wrap body at 72")
      if (match(lines[i], /^(Why|Impact|Risk):[ \t]*/)) {
        label = substr(lines[i], 1, index(lines[i], ":") - 1)
        if (label in field) fail(label ": appears twice")
        if (!("Impact" in field) && label != "Impact") fail(label ": appears before Impact:; Impact comes first")
        if (label == "Why" && ("Risk" in field)) fail("Why: appears after Risk:; order is Impact, Why, Risk")
        field[label] = substr(lines[i], RLENGTH + 1)
        current = label
      } else if (lines[i] == "") {
        current = ""
      } else if (current != "") {
        field[current] = field[current] " " trim(lines[i])
      }
    }
    check_impact("Impact:", field["Impact"])
    if (rank(floor) >= 2 && trim(field["Why"]) == "") fail("Why: is required at " floor " risk")
    if ("Risk" in field) check_level("Risk:", field["Risk"])
    else if (rank(floor) >= 2) fail("Risk: is required at " floor " risk")
    exit (failures > 0)
  }

  first = 1; while (first <= count && trim(lines[first]) == "") first++
  last = count; while (last >= 1 && trim(lines[last]) == "") last--
  if (trim(lines[first]) != start_marker) fail("first line must be " start_marker)
  if (trim(lines[last]) != end_marker) fail("last line must be " end_marker)

  fence = ""
  section = ""
  for (i = first + 1; i < last; i++) {
    line = lines[i]
    if (trim(line) == start_marker || trim(line) == end_marker) fail("line " i ": markers must appear exactly once")
    if (line ~ /^[ \t]*```/) {
      if (fence == "") { fence = line ~ /^[ \t]*```mermaid/ ? "mermaid" : "code"; body[section] = body[section] " " fence }
      else fence = ""
      continue
    }
    if (fence == "mermaid") { if (index(line, ";")) fail("line " i ": ';' breaks mermaid rendering"); continue }
    if (fence == "code") continue
    if (line ~ /^## /) {
      section = trim(substr(line, 4))
      if (section ~ /^Risk:/) { risk_heading = substr(section, 6); section = "Risk" }
      if (section in position) fail("section '" section "' appears twice")
      position[section] = ++order
      continue
    }
    if (section != "") body[section] = body[section] " " trim(line)
    if (section == "Risk" && line ~ /^[ \t]*\|/ && line !~ /^[ \t]*\|[ \t:|-]*$/) risk_rows++
    if (section == "Verification" && line ~ /^[ \t]*[-*] [^ ]/) verification_items++
    if (line !~ /^[ \t]*\|/) prose_words += words(line)
  }
  if (fence != "") fail("code fence is not closed")

  required_count = split("Impact Why Risk Verification", required, " ")
  previous = 0
  for (i = 1; i <= required_count; i++) {
    name = required[i]
    if (!(name in position)) { fail("missing section '## " (name == "Risk" ? "Risk: <level>" : name) "'"); continue }
    if (position[name] < previous) fail("section '" name "' is out of order; required order is Impact, Why, Risk, Verification")
    previous = position[name]
  }
  if (("Impact" in position) && position["Impact"] != 1) fail("first section must be '## Impact'")
  for (name in position) if (trim(body[name]) == "") fail("section '" name "' is empty; omit optional sections instead")
  if (prose_words > 350) fail("recap has " prose_words " words outside tables, code, and diagrams; limit is 350, aim for 250")
  if (("Risk" in position) && risk_rows < 2) fail("## Risk: needs a table with a header and at least one area row")
  if (("Verification" in position) && verification_items < 1) fail("## Verification needs at least one '- ' item: a check and its result, or 'Not verified: ...'")
  if ("Impact" in position) check_impact("## Impact", body["Impact"])
  if ("Risk" in position) check_level("## Risk:", risk_heading)
  exit (failures > 0)
}
