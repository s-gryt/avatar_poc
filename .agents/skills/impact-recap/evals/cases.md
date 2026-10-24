# Eval cases

Each case is a real commit range in this repo. The key impacts are the
ground truth a judge checks against; they were written from the diff alone.

## c1-pr-trigger

- Mode: commit
- Range: `d537540^..d537540`
- Key impacts:
  - Deleting the `push:` line moves `branches: [main]` under `pull_request`.
    Before: the workflow ran on every pull request (any target) and on pushes
    to `main`. After: only pull requests targeting `main` (plus the weekly
    schedule and manual dispatch) run it.
  - Pushes to `main` no longer run docs-guardrails; pull requests into other
    branches no longer run it either.
  - Risk is high: a CI trigger change decides which changes get checked.
- Traps: describing it as "removed push trigger" only, missing that
  `branches` now filters pull requests.

## c2-mixed-cleanup

- Mode: commit
- Range: `cd34738^..cd34738`
- Key impacts:
  - The weekly Monday 06:17 UTC docs-guardrails run stops; only pull requests
    to `main` and manual dispatch run it.
  - The Claude Code project permissions allowlist is removed, including a
    blanket `Bash(*)` and stale entries for another machine's repo, so agents
    in this repo no longer get auto-approved shell commands from project
    settings.
  - Two unrelated concerns in one commit; a good description says so or
    suggests splitting.
- Traps: calling the settings change cosmetic; missing the `Bash(*)`
  security consequence.

## c3-tracker-remote

- Mode: commit
- Range: `b04adef^..b04adef`
- Key impacts:
  - Beads now records `sync.remote` pointing at the GitHub origin, so fresh
    clones can run `bd bootstrap` to restore the issue database, and
    `bd dolt push` / `bd dolt pull` sync issues through `refs/dolt/data`.
  - No source branch content changes; issue data rides a separate ref.
- Traps: describing it as a config tweak with no consequence.

## c4-guardrails-baseline

- Mode: pull request
- Range: `0fab67c^..0fab67c`
- Key impacts:
  - Commits now pass through pre-commit gates: markdownlint, Vale prose
    style, duplicate-prose and duplicate-block detection, a ban on comments
    across file types (unknown file types fail), docs-graph ownership
    checks, link checking, and actionlint.
  - A docs set with a fixed reading order (Engineering to Validation) becomes
    the single authority for design facts.
  - A CI workflow runs the same gates, and a ruleset for `main` is added.
  - Contributors and agents must satisfy these gates to commit; an
    unconfigured file type is now a commit failure.
- Traps: listing 31 files; missing that unknown file types fail.
