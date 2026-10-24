---
name: impact-recap
description: Write commit messages and pull request descriptions that lead with impact (who notices, what behaves differently, what could break, how it was verified) instead of narrating the diff. Use whenever you create a git commit, open a pull request, update a pull request description after new pushes, or the user asks for a commit message, PR summary, PR description, change recap, or impact summary.
---

# Impact recap

A commit message or pull request description exists so a reader can decide
"what does this change mean for me, and can I trust it?" without reading the
diff. The diff already says _what lines moved_. Your text says _what is now
different in the world_.

## The impact test

Before you write a sentence, ask: would it still be true if the same behavior
had been implemented with completely different code?

- Yes: it is **impact**. Keep it. ("Pull requests to `main` now fail when a
  doc links to a missing heading.")
- No: it is **diff narration**. Cut it or move it to `## Changes`.
  ("Added a regex to `tools/docs_graph.py`.")

Impact names an audience (contributors, agents, CI, reviewers, end users,
the tracker) and a consequence (now happens, no longer happens, costs less,
fails earlier, needs a new step). It never opens with an edit verb such as
updated, added, removed, or refactored, and it never names files.

## Ground truth comes from the diff

Write from evidence, not from memory of the session. Session context may
explain _why_; only the diff may support _what_.

```bash
.agents/skills/impact-recap/scripts/facts.sh --staged          # before a commit
.agents/skills/impact-recap/scripts/facts.sh                   # before a PR (base: origin/main)
.agents/skills/impact-recap/scripts/facts.sh --base <rev> --head <rev>
```

`facts.sh` prints commits in scope, per-area file counts, and a **risk floor**
derived from [`scripts/areas.tsv`](scripts/areas.tsv) (first matching path
pattern wins; deleting a file raises it to at least medium). You may rate risk
higher than the floor when the diff justifies it (security exposure, data
loss, irreversible migration, a public interface) and say why. Never rate it
lower.
Read the actual diff (`git diff --cached` or `git diff <merge-base>...HEAD`)
before writing; the facts only tell you where to look. `--no-log` hides commit
subjects when you want to describe the diff without leaning on them.

## Describe effective behavior, before and after

Removed or moved lines can change what the lines around them mean (YAML
nesting, flag defaults, rule order, a deleted override). For each changed
config, workflow, rule, or interface, state the effective behavior **before**
and **after** in one line each, then derive impact from the difference. Do
not stop at "removed X".

## Never invent the why

`Why` comes from the user, the task, an issue, or session context. If none of
them gives a reason, ask the user. If you cannot ask, state only what the diff
evidently fixes and write `(inferred)` after it. If nothing is evident, write
`not stated`. A plausible guess presented as fact is a hallucination.

## Verification is what ran

Risk and Verification name the checks that actually ran and their results.
If nothing ran, say `not verified` and name the check that would verify it.

## Creating a commit

1. Stage one logical change. If `facts.sh --staged` shows unrelated areas,
   split the commit. When a split is not possible (describing an existing
   commit, or the user wants one commit), give each concern its own sentence
   in Impact and say they are unrelated. Take the type and scope from the
   highest-risk concern and name both concerns in the subject.
2. Run `facts.sh --staged`; note the risk floor.
3. Write the message to a temp file in the shape in
   [references/commit.md](references/commit.md).
4. Lint it, passing the floor:
   `scripts/lint.sh commit <file> --risk <floor>`. Fix every finding.
5. Commit with `git commit -F <file>`. Append any attribution trailer the
   harness requires after the body.

## Creating or updating a pull request

1. Push the branch. Run `facts.sh` (or `--base <target>` for a non-main
   target) and read the full diff plus `git log` for the range.
2. Write the recap block in the shape in
   [references/pull-request.md](references/pull-request.md) to a temp file.
3. Lint it: `scripts/lint.sh pr <block> --risk <floor>`. Lint the title with
   `scripts/lint.sh subject <title-file>`.
4. New PR: `gh pr create --title "<title>" --body-file <body>`. The title is
   passed only via `--title`; the body file is the block, markers included,
   followed by any attribution footer the harness requires.
5. Existing PR: `scripts/upsert-pr.sh <number> <block> --risk <floor>`. It
   lints the block, then replaces only the
   text between the markers and leaves everything else (hand-written notes,
   bot summaries, footers) intact. Use `--dry-run` to preview.
6. After a push that changes behavior, regenerate and upsert again so the
   description never describes code that no longer exists.

## Failure modes

- `lint.sh` reports an edit-verb opener or file names in Impact: rewrite the
  sentence around the audience and consequence, not the edit.
- `lint.sh` reports risk below facts: raise the level, or explain in Risk why
  the change is still that risky; you cannot go below the floor.
- `facts.sh` exits 1 with no changes: nothing is staged or the branch equals
  its base. Stage files or check the base.
- `gh pr edit` fails: `upsert-pr.sh <n> <block> --dry-run` prints the merged
  body; apply it by other means.
- Mermaid does not render: no `;` inside the diagram, and keep a blank line
  before and after the fence. `lint.sh` checks the first rule.

## Self-test and evals

- `scripts/test.sh` checks the scripts (lint rules, upsert merge, facts).
- [evals/README.md](evals/README.md) defines the model-graded eval for
  description quality and records the latest results.
