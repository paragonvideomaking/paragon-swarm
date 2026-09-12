---
name: paragon-swarm
description: Run TASK.md through the Paragon independent multi-agent verification pipeline using Test Designer, Test Auditor, Solver, deterministic Runner, and Verifier. Use when the user explicitly asks to run Paragon Swarm, run the swarm, or independently verify TASK.md.
---

# Paragon Swarm

Run the programming task in repository-root `TASK.md` through an isolated multi-agent generation and verification workflow.

Default maximum Solver iterations: 4.

If the user explicitly provides another iteration limit, use it instead.

## Architecture

The workflow is:

TASK
├── Test Designer
│   └── draft hidden tests
│       └── Test Auditor
│           └── final hidden tests
│
└── Solver
    └── candidate

candidate + final hidden tests
        ↓
      Runner
     /      \
  FAIL      PASS
   ↓          ↓
Verifier   VERIFIED
   ↓
Solver

## Critical rule

Do not use one agent to design tests and implement the solution.

Maintain strict information boundaries between roles.

## Phase 1 — Read TASK

Read repository-root:

`TASK.md`

Treat its complete content as the authoritative specification.

If TASK.md is missing or empty, stop and tell the user.

Do not silently invent missing requirements.

## Phase 2 — Start independent branches

Spawn these two custom agents independently and preferably in parallel:

1. `test-designer`
2. `solver`

### Test Designer payload

Send ONLY:

TASK:
<complete TASK.md>

Do not include candidate code because no candidate should exist yet.

### Solver payload

Send ONLY:

TASK:
<complete TASK.md>

Do not include tests.

## Phase 3 — Audit the test design

When `test-designer` returns its Python source, keep the draft in the parent context.

Do not write it into a location visible to Solver yet.

Spawn:

`test-auditor`

Send ONLY:

TASK:
<complete TASK.md>

DRAFT HIDDEN TESTS:
<test-designer output>

Do not send Solver output to Test Auditor.

The Test Auditor returns final executable Python hidden tests.

## Phase 4 — Validate agent outputs

Before execution:

- strip accidental Markdown fences if a coding agent added them;
- ensure Solver output is Python source;
- ensure Auditor output is Python source;
- syntax-check the audited tests without executing them.

If audited tests are syntactically invalid, invoke `test-auditor` again with:

- TASK;
- draft tests;
- syntax error.

Do not involve Solver in test repair.

Allow at most two audit repair attempts.

If the test suite is still invalid, stop and report that verification infrastructure failed.

## Phase 5 — Prepare deterministic runtime

Create:

`.swarm_run/`

Write Solver output to:

`.swarm_run/candidate.py`

Only now write audited tests temporarily to:

`.swarm_run/hidden_tests.py`

The hidden-test file must not exist while a Solver agent is running.

## Phase 6 — Run

Execute the tests with the runtime working directory set to `.swarm_run`.

Do not weaken the user's current sandbox or permission policy.

Do not expose secrets.

Do not enable network access for generated code merely to make it pass.

Capture:

- exit code;
- stdout;
- stderr.

Immediately after capturing the result, delete:

`.swarm_run/hidden_tests.py`

Keep the audited hidden-test source only in the parent orchestration context.

## Phase 7 — Success condition

Accept the candidate ONLY when both are true:

1. process exit code is 0;
2. output contains exactly:

`[VERIFIED] all hidden tests passed`

If both conditions are satisfied, stop.

Report:

- VERIFIED;
- number of Solver iterations;
- runtime if available;
- artifact path `.swarm_run/candidate.py`.

Never claim mathematical proof or absolute correctness.

Say only that the candidate passed the independently generated and audited test suite.

## Phase 8 — Failure handling

If Runner fails, spawn custom agent:

`verifier`

The hidden-test file must already have been deleted.

Send ONLY:

TASK:
<complete TASK.md>

CANDIDATE:
<current candidate.py>

RUNNER OUTPUT:
<captured stdout/stderr>

Do not send hidden-test source.

## Phase 9 — Repair iteration

When Verifier returns its repair brief, spawn a FRESH `solver` agent.

Send:

TASK:
<complete TASK.md>

PREVIOUS CANDIDATE:
<current candidate source>

REPAIR BRIEF:
<Verifier output>

Do not send hidden tests.

When the new Solver returns:

1. replace `.swarm_run/candidate.py`;
2. recreate `.swarm_run/hidden_tests.py` from the audited tests held by the parent;
3. run again;
4. capture output;
5. delete hidden_tests.py again.

Repeat until VERIFIED or the iteration limit is reached.

## Failure after iteration budget

If the iteration limit is exhausted, return:

`[FAILED] iteration budget exhausted`

Also report:

- number of iterations;
- last Runner failure;
- final candidate path.

Do not change the hidden tests merely because Solver cannot pass them.

If there is evidence that the tests themselves contradict TASK, stop and explicitly report an infrastructure conflict instead of silently weakening the tests.

## Security

Generated candidate code and generated tests are untrusted code.

Never:

- disable the host sandbox;
- expose production secrets;
- expose SSH keys;
- expose cloud credentials;
- expose wallet files;
- grant network access simply to make the candidate succeed.

Use the coding environment's existing sandbox and permission controls.
