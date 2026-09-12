# Paragon AI Swarm

This repository contains the Paragon multi-agent verification workflow.

`TASK.md` is the primary user-editable task specification.

When the user explicitly asks to:

- run Paragon Swarm;
- run the swarm;
- verify TASK.md independently;
- solve TASK.md using independent agents;

use the `/paragon-swarm` skill.

Do not automatically run the full swarm for normal coding questions unless the user requests it.

The available project subagents are:

- `test-designer`
- `test-auditor`
- `solver`
- `verifier`

Maintain strict information boundaries:

- Test Designer sees TASK only.
- Test Auditor sees TASK + draft tests only.
- Solver never sees hidden tests.
- Verifier sees TASK + candidate + Runner output, but never hidden-test source.

The main Claude Code session acts as orchestrator.

The Runner is deterministic local execution, not an AI agent.

Temporary generated artifacts belong in `.swarm_run/`.

Never weaken Claude Code permissions or sandboxing to execute AI-generated code.
