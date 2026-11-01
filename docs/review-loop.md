# Developer/critic review loop

Changes to this repository go through a two-agent loop defined in
`.claude/agents/`. The critic never edits; the developer never approves its own
work.

```
            findings                        diff
  critic  ----------->  developer  -------------------->  critic
    ^                                                       |
    |               CHANGES REQUESTED                       |
    +-------------------------------------------------------+
                         APPROVE -> open PR, CI runs
```

1. **Audit.** Run the `critic` agent with "full audit" (or a git range such as
   `main..HEAD`). It returns findings ranked blocker, major, minor, nit, each
   with evidence, and a verdict.
2. **Fix.** Run the `developer` agent with the findings. It reproduces each one,
   adds a failing test for real bugs, fixes it, and declines findings it can show
   are wrong. If simulation output changes, it re-runs the whole pipeline and
   updates every number in the README and paper.
3. **Re-review.** Run a fresh `critic` on the new range. It checks that each fix
   works and looks for regressions.
4. Repeat until the critic returns `VERDICT: APPROVE`, with at most three rounds.
   Anything still open after three rounds goes into the pull request description
   for a human decision.

With Claude Code, for example:

```
> Use the critic agent to do a full audit.
> Use the developer agent to address these findings: <paste>
> Use a fresh critic agent to review main..HEAD.
```

## Checks every round must pass

```bash
python -m pytest -q        # unit tests in tests/
python run_sanity.py       # behavioral verification; exits non-zero on failure
```

CI (`.github/workflows/ci.yml`) runs both on every push and pull request.
