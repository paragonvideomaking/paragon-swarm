---
name: paragon-swarm
description: Run TASK.md through the Paragon independent multi-agent verification pipeline using Test Designer, Test Auditor, Solver, deterministic Runner, and Verifier. Use when the user explicitly asks to run Paragon Swarm or independently verify TASK.md.
---

# Paragon Swarm

Run repository-root `TASK.md` through the Paragon independent generation and verification workflow.

Default maximum Solver iterations: 4.

Use a different limit only if the user explicitly requests one.

## Roles

Use the project subagents:

- `test-designer`
- `test-auditor`
- `solver`
- `verifier`

The current Claude Code session is the orchestrator.

The Runner is ordinary local execution and must not be replaced by another AI opinion.

## Isolation rules

These boundaries are mandatory:

### Test Designer receives

TASK only.

### Test Auditor receives

TASK + draft hidden tests only.

### Solver receives

TASK only on iteration 1.

On repair iterations:

TASK + previous candidate + Verifier repair brief.

Solver never receives hidden tests.

### Verifier receives

TASK + current candidate + sanitized Runner output.

Verifier never receives hidden-test source.

### Never send

Candidate source to:

- Test Designer;
- Test Auditor.

Hidden-test source to:

- Solver;
- Verifier.

## Step 1 — Read TASK

Read repository-root:

`TASK.md`

If it is missing or empty, stop.

Do not invent missing requirements.

## Step 2 — Start two independent branches

Spawn `test-designer` and `solver` as separate subagents.

Start them in parallel when possible.

Send Test Designer:

TASK:
<complete TASK>

Send Solver:

TASK:
<complete TASK>

Do not include additional information.

## Step 3 — Audit tests

When Test Designer returns, retain the draft tests in the main orchestration context.

Do NOT write hidden tests into the repository yet.

Spawn:

`test-auditor`

Send:

TASK:
<complete TASK>

DRAFT HIDDEN TESTS:
<Test Designer output>

Do not send Solver output.

Receive the final audited test suite.

## Step 4 — Validate outputs

Strip accidental Markdown fences if necessary.

Ensure:

- Solver output is Python source;
- audited tests are Python source.

Syntax-check audited tests without executing them.

If the audited suite is invalid Python, run Test Auditor again with:

- TASK;
- original draft;
- syntax error.

Allow at most two audit repair attempts.

If it still fails, stop and report verification-infrastructure failure.

## Step 5 — Runtime

Create:

`.swarm_run/`

Write Solver output to:

`.swarm_run/candidate.py`

Only after the current Solver subagent has completed, write audited tests temporarily to:

`.swarm_run/hidden_tests.py`

This ordering is important: Solver must never have an opportunity to read the hidden tests.

## Step 6 — Execute

Run the test suite from `.swarm_run`.

Use the current Claude Code sandbox and permission model.

Do not loosen permissions.

Capture:

- exit code;
- stdout;
- stderr.

Immediately delete:

`.swarm_run/hidden_tests.py`

after capturing Runner output.

Keep the audited test source only in the main orchestrator context.

## Step 7 — VERIFIED

Accept the candidate only if:

1. exit code is 0;
2. output contains exactly:

`[VERIFIED] all hidden tests passed`

If verified, report:

- `[VERIFIED]`;
- number of Solver iterations;
- execution time if available;
- artifact: `.swarm_run/candidate.py`.

Do not claim absolute correctness.

State that the candidate passed an independently generated and audited test suite.

## Step 8 — Failure

If Runner fails, ensure `hidden_tests.py` has already been deleted.

Spawn:

`verifier`

Send only:

TASK:
<complete TASK>

CANDIDATE:
<current candidate>

RUNNER OUTPUT:
<stdout/stderr>

Never send hidden tests.

## Step 9 — Retry

Receive Verifier repair brief.

Spawn a FRESH `solver` subagent.

Send:

TASK:
<complete TASK>

PREVIOUS CANDIDATE:
<current candidate>

REPAIR BRIEF:
<Verifier output>

Do not send hidden tests.

When Solver returns:

1. replace `.swarm_run/candidate.py`;
2. recreate temporary `.swarm_run/hidden_tests.py`;
3. execute;
4. capture output;
5. delete hidden_tests.py.

Repeat until VERIFIED or iteration limit.

## Iteration budget exhausted

If the candidate does not pass within the limit, stop with:

`[FAILED] iteration budget exhausted`

Report:

- iteration count;
- last sanitized Runner failure;
- current candidate path.

Do not weaken or rewrite valid hidden tests merely to obtain a green result.

If evidence suggests the tests contradict TASK, report:

`[INFRASTRUCTURE CONFLICT]`

and explain the contradiction.

## Security

Candidate code and test code are AI-generated and untrusted.

Never:

- disable Claude Code sandboxing;
- bypass permission checks;
- expose `.env` secrets;
- expose SSH keys;
- expose cloud credentials;
- expose wallet files;
- grant network access only to make tests pass.

Run generated code only with the environment's existing restrictions.
