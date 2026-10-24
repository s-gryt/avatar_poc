# impact-recap evals

Measures whether the skill makes descriptions explain impact rather than
narrate the diff, without losing accuracy. The script self-test
(`scripts/test.sh`) is separate; this eval grades model output.

## Protocol

1. **Cases.** [cases.md](cases.md) lists real commit ranges from this repo
   with ground-truth key impacts and traps. Generators never see it.
2. **Generate.** Two generator runs on a mid-tier model (Sonnet), same cases:
   - _baseline_: "write a commit message / PR description", diff only, no
     access to the skill, `AGENTS.md`, or original commit messages.
   - _skill_: follows `SKILL.md`, may run `facts.sh` and `lint.sh`, diff
     only, no access to original commit messages or this folder.
3. **Lint.** Run `scripts/lint.sh` on every output at the `facts.sh` risk
   floor. Baseline outputs are not expected to pass; the pass rate is a
   format signal only.
4. **Judge.** A small model (Haiku) grades each output blind: outputs are
   shuffled and labeled X/Y per case, and the judge does not know which run
   produced which. It scores against `cases.md` with the rubric below.
5. **Record.** Append a dated entry under Results with per-case scores, lint
   results, and any skill changes the run prompted.

## Rubric

Each dimension scores 1 to 5.

| Dimension | 5 means |
| --------- | ------- |
| Impact-first | Opens with who notices and what is different; diff detail is secondary or absent. |
| Accuracy | Covers every key impact; states nothing the diff does not support. |
| Traps | Avoids every trap listed for the case. |
| Risk calibration | States risk at a level and with a reason that matches the change. |
| Concision | Every sentence earns its place; no file inventory. |

A run passes when the skill output beats baseline on Impact-first and
Traps on average, does not score lower on Accuracy, and every skill output
passes `lint.sh`.

## Results

Entries are appended by the person or agent running the eval.

### 2026-10-23

Generator: Sonnet. Judge: Haiku, blind, X/Y shuffled per case. Baseline
outputs are shared by both runs; v2 and v3 differ only in the skill text.
Diffs were read raw (`rtk bypass`) and the skill run used `facts.sh --no-log`,
so neither run saw the original commit messages.

Totals out of 25 per case:

| Case | Baseline (v2 judge) | Skill v2 | Baseline (v3 judge) | Skill v3 |
| ---- | ------------------- | -------- | ------------------- | -------- |
| c1-pr-trigger | 15 | 23 | 17 | 24 |
| c2-mixed-cleanup | 13 | 23 | 14 | 19 |
| c3-tracker-remote | 10 | 19 | 10 | 19 |
| c4-guardrails-baseline | 7 | 21 | 8 | 16 |
| **Total** | **45** | **86** | **49** | **78** |

Averages per dimension (baseline / skill):

| Dimension | v2 | v3 |
| --------- | -- | -- |
| Impact-first | 1.75 / 4.00 | 1.50 / 4.00 |
| Accuracy | 2.50 / 4.25 | 3.25 / 3.75 |
| Traps | 2.25 / 5.00 | 2.25 / 4.25 |
| Risk calibration | 1.00 / 4.75 | 1.50 / 4.25 |
| Concision | 3.75 / 3.50 | 3.75 / 3.25 |

Lint: 8/8 skill outputs pass (v2 and v3); 0/4 baseline outputs pass.

Verdict: **pass** on both runs (Impact-first and Traps higher, Accuracy not
lower, every skill output lints).

Findings and changes made:

- A first run (v1, discarded) leaked original commit subjects through
  `facts.sh`; added `--no-log`.
- v1 skill output missed the c1 trap (`branches` re-attaching to
  `pull_request`) and invented a reason. Added "Describe effective
  behavior, before and after" and "Never invent the why"; v2 and v3 both
  caught the trap.
- v2 judge: commit body led with Why, and the PR recap repeated facts across
  Impact, Changes, and Flow. Reordered to Impact first (lint-enforced),
  added once-per-fact and diagram rules, and a 350-word prose limit.
- Concision stays the weakest dimension: skill outputs are longer than
  one-line baselines by design, and large PR recaps still drift toward
  inventories. The same baseline text scored up to 2 points apart between
  judge runs, so per-case differences under 3 points are noise.
