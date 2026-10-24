# Commit message shape

```text
<type>(<scope>): <outcome, imperative, 72 chars max, no period>

Impact: <who or what notices, and what is now different for them>
Why: <the problem or pressure that made this change necessary>
Risk: <low|medium|high> - <what could break and how you checked>

<optional: one short paragraph of notable implementation detail>
```

- `type` is one of feat, fix, docs, ci, build, chore, refactor, perf, test,
  style, revert. `scope` is the area from `facts.sh` or a narrower name.
- The subject states the outcome ("run docs checks only on pull requests"),
  not the edit ("update workflow file").
- `Impact:` comes first and is always required, at least 8 words.
- `Why:` never guesses: mark a reason the diff only implies with
  `(inferred)`. `Risk:` names what ran, or says `not verified`.
- `Why:` and `Risk:` are required when the risk floor is medium or high.
  For low-risk commits they are optional; include them when they add signal.
- Wrap body lines at 72 characters. Continuation lines belong to the label
  above them until a blank line.
- Implementation detail is allowed only after the labeled lines, and only when
  a future reader of `git log` needs it to understand a non-obvious choice.

## Example

```text
ci(guardrails): run docs checks only on pull requests to main

Impact: Contributors get one docs-guardrails run per pull request;
direct pushes to branches no longer start it.
Why: Feature-branch pushes ran the docs gate twice, once on push and
once on the pull request, doubling CI minutes for no new signal.
Risk: high - a wrong trigger would let unchecked docs merge; verified
by opening a draft PR and watching the check start.
```

## Counter-example

```text
ci: update workflow

Impact: Updated docs-guardrails.yml to remove the push trigger.
```

Subject names the edit, Impact opens with an edit verb and names a file, and
a high-risk CI change carries no Why or Risk. `lint.sh` rejects the message.
