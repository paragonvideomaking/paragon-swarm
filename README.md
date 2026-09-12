# Paragon AI Swarm

**Multi-agent verification infrastructure for Claude Code, Codex and standalone AI APIs.**

Paragon AI Swarm is an experimental multi-agent system that separates code generation from code verification.

Instead of asking one AI agent to:

- solve a programming task;
- write its own tests;
- check its own implementation;
- decide whether the result is correct;

Paragon splits the process between independent AI roles and a deterministic local Runner.

The same verification architecture can be used in three ways:

- **Claude Code** — native agents and `/paragon-swarm` orchestration;
- **Codex** — native subagents coordinated through `AGENTS.md`;
- **Standalone Python** — direct API access with your own model, provider and `base_url`.

The core rule is the same in every mode:

> **The Solver never sees the hidden tests.**

The Runner is not an AI agent. It executes the generated candidate against independently generated and audited tests using ordinary local Python.

A result is accepted only when the Runner returns:

```text
[VERIFIED] all hidden tests passed
```

---

## Quick Start

### Claude Code — recommended

1. Clone the repository.
2. Edit `TASK.md`.
3. Open the repository in Claude Code.
4. Run:

```text
/paragon-swarm
```

Claude Code uses the agents in `.claude/agents/` and the orchestration skill in `.claude/skills/paragon-swarm/SKILL.md`.

No API key is required by this repository for the Claude Code mode itself.

---

### Codex — recommended

1. Clone the repository.
2. Edit `TASK.md`.
3. Open the repository in Codex.
4. Ask:

```text
Run Paragon Swarm on TASK.md
```

The main Codex session follows `AGENTS.md` and launches the independent agents defined in `.codex/agents/`.

No API key is required by this repository for the Codex mode itself.

---

### Standalone Python

Use the standalone version when you want:

- your own model;
- your own API provider;
- an OpenAI-compatible endpoint;
- a custom `base_url`;
- explicit control over orchestration and iteration limits.

The Python implementation lives in:

```text
standalone/
```

The standalone mode requires API/provider configuration through `.env`.

See [Standalone Python](#standalone-python-1) for setup instructions.

---

## Watch the full video

We built and explained this infrastructure in a Paragon YouTube video about autonomous AI agents, multi-agent systems, AI verification and agent swarms.

**YouTube video:**  
https://youtu.be/XlUspPYD5is

**Paragon YouTube channel:**  
https://www.youtube.com/@Paragon_zone?sub_confirmation=1

**Paragon Telegram:**  
https://t.me/paragonzone

In Telegram we also publish AI tools, prompts, experiments, free AI access methods and additional materials from our videos.

---

## Why this project exists

You can give one AI agent a prompt like:

> Write the code, create tests, run them and fix your mistakes.

It can do all of that.

But there is an obvious weakness: the same AI context writes the implementation and then decides how that implementation should be tested.

The model already knows:

- its own assumptions;
- its own architecture;
- its own shortcuts;
- the implementation it just produced.

That makes the verification process less independent.

Paragon AI Swarm separates those responsibilities into isolated roles and contexts.

```text
                         TASK.md
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
        TEST DESIGNER                   SOLVER
              │                           │
              ▼                           │
        TEST AUDITOR                      │
              │                           │
              ▼                           ▼
          FINAL TESTS                 CANDIDATE
              │                           │
              └─────────────┬─────────────┘
                            ▼
                          RUNNER
                       ┌────┴────┐
                       │         │
                     FAIL       PASS
                       │         │
                       ▼         ▼
                   VERIFIER  [VERIFIED]
                       │
                       └──────────→ SOLVER
```

The Solver and Test Designer can work in parallel because neither needs access to the other's output.

The test branch is audited independently before execution.

Only when the candidate and final tests are ready are they written to runtime files and passed to the Runner.

---

## Core architecture

### 1. `TASK.md`

`TASK.md` is the main file a normal user changes.

It stays in the repository root regardless of which mode you use.

It describes:

- what needs to be implemented;
- expected input and output;
- constraints;
- required behavior;
- edge cases if they are part of the specification.

Example:

```text
Implement an LRU cache with a fixed capacity.

Requirements:
- get(key)
- put(key, value)
- O(1) average access
- evict least recently used items
```

The rest of the infrastructure can stay unchanged.

---

### 2. Test Designer

The **Test Designer** receives only `TASK.md`.

It does not see the Solver implementation.

Its job is to generate an independent hidden test suite covering:

- normal cases;
- boundary conditions;
- edge cases;
- invariants;
- ordering;
- mutations and side effects;
- explicit requirements from the task.

In native Claude Code and Codex modes, the draft tests should remain inside the orchestrator/test branch while the Solver is working.

They are not exposed to the Solver.

---

### 3. Test Auditor

The **Test Auditor** receives:

- `TASK.md`;
- the draft hidden tests.

It still does not see the Solver implementation.

Its task is to audit the tests themselves.

It checks whether the tests:

- cover the important requirements;
- invent requirements that are not present in the task;
- contradict the specification;
- depend on one specific implementation;
- miss important edge cases;
- contain invalid or weak verification logic.

This means the system does not only verify the solution.

It also verifies the verification process.

---

### 4. Solver

The **Solver** receives:

- `TASK.md`;
- feedback from previous failed iterations, if any.

It never receives the hidden tests.

Its job is to produce the best implementation possible from the specification.

When the branch is ready, the generated implementation is written to:

```text
.swarm_run/candidate.py
```

---

### 5. Runner

The **Runner is not an AI agent.**

This is a core design rule of Paragon AI Swarm.

The Runner executes ordinary Python locally:

```text
candidate.py
+
hidden_tests.py
```

and collects the real execution result:

- stdout;
- stderr;
- exit code;
- traceback.

If all audited hidden tests pass, the Runner returns:

```text
[VERIFIED] all hidden tests passed
```

If something fails, the actual execution output is sent to the Verifier.

The final test is therefore based on deterministic code execution, not on an AI agent deciding whether another AI agent looks correct.

---

### 6. Verifier / Critic

The **Verifier** receives:

- the original task;
- the current candidate implementation;
- the real Runner output.

Its job is not to rewrite the whole solution.

It diagnoses the failure and produces a compact repair brief for the Solver.

Example:

```text
The implementation violates partial-fill accounting.

Remaining quantity is decremented twice when the buy order is only partially filled.
```

The Solver receives this feedback and creates the next version.

The loop continues until:

```text
[VERIFIED]
```

or until the configured iteration limit is reached.

---

## Runtime isolation

Generated solutions and hidden tests do not live beside the permanent agent instructions.

Runtime files are written to:

```text
.swarm_run/
├── hidden_tests_draft.py
├── hidden_tests.py
└── candidate.py
```

`.swarm_run/` should be gitignored.

In native Claude Code and Codex modes, the preferred flow is:

```text
Test Designer
    ↓
draft tests stay inside the test/orchestrator context
    ↓
Test Auditor
    ↓
final tests stay isolated

Solver works separately in parallel

        ↓ both branches ready ↓

.swarm_run/candidate.py
.swarm_run/hidden_tests.py
        ↓
      Runner
```

The important property is not merely hiding a file name.

The Solver should never receive or inspect the hidden test content before producing its candidate.

---

## Project structure

```text
paragon-swarm/
│
├── TASK.md
├── README.md
├── AGENTS.md
├── CLAUDE.md
├── LICENSE
├── .gitignore
├── .env.example
│
├── .claude/
│   ├── agents/
│   │   ├── test-designer.md
│   │   ├── test-auditor.md
│   │   ├── solver.md
│   │   └── verifier.md
│   └── skills/
│       └── paragon-swarm/
│           └── SKILL.md
│
├── .agents/
│   └── skills/
│       └── paragon-swarm/
│           └── SKILL.md
│
├── .codex/
│   ├── config.toml
│   └── agents/
│       ├── test-designer.toml
│       ├── test-auditor.toml
│       ├── solver.toml
│       └── verifier.toml
│
├── standalone/
│   ├── swarm.py
│   └── ai_system/
│       ├── TEST_DESIGNER_SYSTEM.md
│       ├── TEST_AUDITOR_SYSTEM.md
│       ├── SOLVER_SYSTEM.md
│       └── VERIFIER_SYSTEM.md
│
└── .swarm_run/       # generated at runtime, gitignored
```

---

## Claude Code

Claude Code is one of the recommended ways to run Paragon AI Swarm because the multi-agent roles can be represented directly as native agents.

### Agent files

```text
.claude/agents/
├── test-designer.md
├── test-auditor.md
├── solver.md
└── verifier.md
```

Each file describes one isolated role.

#### `test-designer.md`

Receives only the task specification and creates an independent test suite.

It must not receive the Solver implementation.

#### `test-auditor.md`

Receives the task and the Test Designer output.

It audits the hidden tests against the original specification without seeing the Solver implementation.

#### `solver.md`

Receives only the task and repair feedback from previous failed iterations.

It must never receive hidden tests.

#### `verifier.md`

Receives the task, current candidate and real Runner output.

It diagnoses the failure and sends a repair brief back to the Solver.

---

### Claude Code orchestration

The skill lives in:

```text
.claude/skills/paragon-swarm/SKILL.md
```

Its orchestration logic is:

```text
1. Read TASK.md
2. Start Test Designer and Solver independently
3. Send Test Designer output to Test Auditor
4. Never expose hidden tests to Solver
5. When both branches are ready, write candidate.py and hidden_tests.py
6. Run candidate against audited hidden tests locally
7. If PASS → VERIFIED
8. If FAIL → run Verifier
9. Send Verifier feedback to Solver
10. Repeat until VERIFIED or the iteration limit is reached
```

Run it with:

```text
/paragon-swarm
```

---

## Codex

Codex uses the same architecture, but orchestration is driven by the repository-level `AGENTS.md` and native agent definitions.

### Agent files

```text
.codex/agents/
├── test-designer.toml
├── test-auditor.toml
├── solver.toml
└── verifier.toml
```

The four roles follow the same isolation rules as the Claude Code version.

The repository-level:

```text
AGENTS.md
```

tells the main Codex session how to coordinate the infrastructure.

Conceptually:

```text
TASK
 ↓
Test Designer ─→ Test Auditor ─→ Tests
 ↓
Solver ─────────────────────────→ Candidate
                                  ↓
                                Runner
                              /        \
                           FAIL        PASS
                            ↓            ↓
                         Verifier    VERIFIED
                            ↓
                          Solver
```

The user does not launch the Python orchestrator in this mode.

Open the repository in Codex and ask:

```text
Run Paragon Swarm on TASK.md
```

The main session coordinates the subagents according to `AGENTS.md`.

---

## Standalone Python

The standalone implementation is for users who want direct API control.

It lives in:

```text
standalone/
├── swarm.py
└── ai_system/
    ├── TEST_DESIGNER_SYSTEM.md
    ├── TEST_AUDITOR_SYSTEM.md
    ├── SOLVER_SYSTEM.md
    └── VERIFIER_SYSTEM.md
```

`TASK.md` still remains in the repository root.

The standalone orchestrator reads:

```text
../TASK.md
```

relative to `standalone/swarm.py`.

### Requirements

- Python 3.11+
- OpenAI-compatible API
- API key for your model provider

Clone the repository:

```bash
git clone https://github.com/paragonvideomaking/paragon-swarm.git
cd paragon-swarm
```

Create a virtual environment:

```bash
python -m venv .venv
```

Linux / macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -U openai python-dotenv
```

Create the environment file:

```bash
cp .env.example .env
```

Configure `.env`:

```env
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-5.6-sol
OPENAI_BASE_URL=
SWARM_MAX_ITERS=4
```

Edit the root task:

```text
TASK.md
```

Then start the standalone orchestrator:

```bash
cd standalone
python swarm.py
```

The standalone mode generates runtime files under the repository-level `.swarm_run/` directory.

---

## Claude Code / Codex vs Standalone

| Mode | Orchestration | Agent definitions | API configuration in repo | Best for |
|---|---|---|---|---|
| Claude Code | Native Claude Code command | `.claude/agents/` | Not required | Fast native multi-agent workflow |
| Codex | Main Codex session + `AGENTS.md` | `.codex/agents/` | Not required | Native Codex subagent workflow |
| Standalone Python | `standalone/swarm.py` | `standalone/ai_system/` | Required | Custom models, providers and full API control |

All three modes preserve the same core architecture:

- independent test generation;
- independent test auditing;
- hidden tests isolated from Solver;
- deterministic local execution;
- Verifier feedback only after a real failure.

---

## Example execution

The exact interface differs by mode, but conceptually a run looks like this:

```text
[SWARM] reading TASK.md

[TEST DESIGNER] generating draft hidden tests...
[SOLVER] generating candidate independently...

[TEST AUDITOR] auditing hidden tests...
[TEST AUDITOR] final test suite ready

[SOLVER] candidate ready

[RUNTIME]
  wrote .swarm_run/candidate.py
  wrote .swarm_run/hidden_tests.py

[RUNNER]
  AssertionError: partial fill quantity is incorrect

[VERIFIER]
  The implementation violates partial-fill accounting...

[SOLVER]
  generating repaired candidate...

[RUNNER]
  [VERIFIED] all hidden tests passed

[VERIFIED] candidate accepted
```

The important part is the information boundary:

```text
Solver → does not see hidden tests
Test Designer → does not see Solver implementation
Test Auditor → does not see Solver implementation
Runner → executes real Python
Verifier → reacts to real Runner output
```

---

## Use it for another task

Normally, the only file a user needs to change is:

```text
TASK.md
```

For example:

```text
Implement a rate limiter with a fixed request window.
```

Then choose one of the three execution modes:

### Claude Code

```text
/paragon-swarm
```

### Codex

```text
Run Paragon Swarm on TASK.md
```

### Standalone Python

```bash
cd standalone
python swarm.py
```

The infrastructure then:

1. reads the task;
2. starts independent generation and verification branches;
3. generates hidden tests;
4. audits the hidden tests;
5. generates a candidate without revealing those tests;
6. writes the candidate and final tests to runtime files;
7. executes them locally;
8. analyzes failures;
9. sends compact feedback back to the Solver;
10. iterates until `[VERIFIED]` or the iteration limit is reached.

---

## Why independent AI agents?

The central idea of this project is simple:

**generation and verification should not live inside the same AI context.**

A single AI agent can write code and then test itself.

But then the same context is effectively:

- developer;
- test designer;
- reviewer;
- judge.

Paragon AI Swarm separates those roles.

The Test Designer does not see the implementation.

The Test Auditor does not see the implementation.

The Solver does not see the hidden tests.

The Runner is not an AI model at all.

The Verifier only works with the real result of execution.

This does not make the system perfect.

Different roles can still share biases, especially if they use the same underlying model.

But it removes one obvious failure mode:

> one AI implementation designing its own exam around its own assumptions.

---

## Why keep the Runner non-AI?

The independent agents generate, audit, solve and diagnose.

But the final check should not be another language-model opinion.

The Runner executes:

```text
candidate.py + hidden_tests.py
```

That gives the orchestration layer a concrete result to work with:

- the program passed;
- the program failed;
- this assertion failed;
- this exception occurred;
- this traceback was produced.

The Verifier can interpret that evidence, but it does not replace the execution itself.

---

## Important security note

This project executes Python code generated by AI.

That includes:

- generated candidate implementations;
- generated hidden test suites.

Do not run untrusted AI-generated code with access to:

- production credentials;
- SSH keys;
- private repositories;
- personal files;
- cloud credentials;
- cryptocurrency wallets;
- sensitive environment variables.

For serious use, execute the Runner inside an isolated container or sandbox with:

- minimal permissions;
- no production secrets;
- filesystem isolation;
- network restrictions;
- CPU and memory limits;
- execution time limits.

The current repository is an experimental demonstration, not a production security boundary.

---

## What this project explores

Paragon AI Swarm is an experiment around:

- AI agents;
- AI agent swarms;
- multi-agent systems;
- agentic AI;
- autonomous AI agents;
- Claude Code agents;
- Codex agents;
- multi-agent coding;
- AI code verification;
- AI-generated tests;
- independent AI verification;
- Test Designer agents;
- Test Auditor agents;
- Solver / Critic architectures;
- external validation;
- hidden tests;
- AI orchestration;
- deterministic runners;
- scalable AI systems;
- AI safety;
- AI monitoring.

The project demonstrates the difference between a single AI chat and a system where generation, testing, execution and verification are separated into independent processes.

---

## Paragon

**Paragon** is a YouTube and Telegram project about artificial intelligence, AI agents, automation, coding agents, Web3 and practical experiments with modern AI systems.

### Links

- **YouTube video:** https://youtu.be/XlUspPYD5is
- **YouTube channel:** https://www.youtube.com/@Paragon_zone?sub_confirmation=1
- **Telegram:** https://t.me/paragonzone
- **GitHub repository:** https://github.com/paragonvideomaking/paragon-swarm

---

## Repository description

Recommended GitHub description:

```text
Multi-agent verification infrastructure for Claude Code, Codex and standalone AI APIs.
```

Recommended GitHub topics:

```text
ai-agents
multi-agent
multi-agent-systems
agentic-ai
autonomous-agents
claude-code
codex
ai-verification
ai-testing
ai-swarm
llm
python
ai-orchestration
multi-agent-coding
```

---

## Keywords

`AI agents` · `AI agent swarm` · `multi-agent system` · `agentic AI` · `Claude Code agents` · `Codex agents` · `AI verification` · `AI testing` · `independent verification` · `LLM agents` · `Solver Critic` · `Test Designer` · `Test Auditor` · `Python agents` · `autonomous agents` · `AI orchestration` · `multi-agent coding` · `AI code verification` · `hidden tests` · `Paragon AI`

---

## License

MIT License. See [LICENSE](LICENSE) for the full text.

---

## Disclaimer

This project is experimental.

`[VERIFIED]` means that the generated implementation passed the generated and audited hidden test suite.

It does **not** mathematically prove that:

- the implementation is correct for every possible input;
- the hidden tests are perfect;
- the AI agents interpreted the specification correctly;
- the system is safe for production use.
