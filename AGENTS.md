# Paragon AI Swarm

This repository contains the Paragon multi-agent verification workflow.

## Primary user input

`TASK.md` is the task specification.

The user normally changes only `TASK.md`.

## Running the swarm

When the user explicitly asks to:

- run Paragon Swarm;
- run the swarm;
- independently verify TASK.md;
- solve TASK.md with independent agents;

use the `paragon-swarm` skill.

Do not run the full swarm automatically for ordinary coding requests unless the user asks for it.

## Core isolation rule

Generation and verification must remain separated.

Never allow one agent to simultaneously:

1. implement the solution;
2. design the hidden tests;
3. judge whether its own solution is correct.

Use the dedicated custom agents:

- `test-designer`
- `test-auditor`
- `solver`
- `verifier`

The deterministic Runner is executed by the parent Codex session and is not an AI agent.

## Information boundaries

`test-designer` receives:
- TASK only.

`test-auditor` receives:
- TASK;
- draft hidden tests.

`solver` receives:
- TASK;
- on retries, previous candidate and Verifier repair brief.

`verifier` receives:
- TASK;
- candidate source;
- sanitized Runner output.

Never send hidden-test source to Solver or Verifier.

Never send candidate source to Test Designer or Test Auditor.

## Runtime

Temporary execution artifacts belong in:

`.swarm_run/`

Do not commit generated hidden tests or candidates.

Do not weaken the current sandbox or permission mode in order to run generated code.
