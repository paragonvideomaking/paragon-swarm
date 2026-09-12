#!/usr/bin/env python3
"""Paragon mini-swarm demo: Solver -> Runner -> Verifier/Critic.

The script asks one model instance to act as three isolated roles. Solver never sees
hidden tests directly. Runner executes candidate.py locally. Verifier only receives
test output and turns failures into actionable feedback for the next Solver pass.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-sol")
BASE_URL = os.getenv("OPENAI_BASE_URL", "")
MAX_ITERS = int(os.getenv("SWARM_MAX_ITERS", "4"))
RUN_TIMEOUT = 20
BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent

TASK_PATH = REPO_ROOT / "TASK.md"
AI_SYSTEM_DIR = BASE_DIR / "ai_system"
WORKDIR = REPO_ROOT / ".swarm_run"
CANDIDATE = WORKDIR / "candidate.py"
TEST_FILE = WORKDIR / "hidden_tests.py"

def read_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    return path.read_text(
        encoding="utf-8"
    ).strip()


def read_system_prompt(name: str) -> str:
    return read_file(
        AI_SYSTEM_DIR / f"{name}.md"
    )

TASK = read_file(TASK_PATH)
TEST_DESIGNER_SYSTEM = read_system_prompt("TEST_DESIGNER_SYSTEM")
TEST_AUDITOR_SYSTEM = read_system_prompt("TEST_AUDITOR_SYSTEM")
SOLVER_SYSTEM = read_system_prompt("SOLVER_SYSTEM")
VERIFIER_SYSTEM = read_system_prompt("VERIFIER_SYSTEM")
HIDDEN_TESTS_DRAFT_PATH = (AI_SYSTEM_DIR / "HIDDEN_TESTS_DRAFT.md")
HIDDEN_TESTS_PATH = (AI_SYSTEM_DIR / "HIDDEN_TESTS.md")

def strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        t = "\n".join(lines)
    return t.strip() + "\n"


def call_role(client: OpenAI, system: str, user: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content.strip()

def validate_python(source: str, label: str) -> None:
    try:
        compile(source, label, "exec")
    except SyntaxError as exc:
        raise RuntimeError(
            f"{label} contains invalid Python: {exc}"
        ) from exc

def generate_hidden_tests(client: OpenAI) -> str:
    print("[TEST DESIGNER] generating draft hidden tests...")

    designer_input = (
        "TASK SPECIFICATION:\n"
        f"{TASK}\n\n"
        "Create an independent hidden Python test suite."
    )

    draft = strip_fences(
        call_role(
            client,
            TEST_DESIGNER_SYSTEM,
            designer_input,
        )
    )

    validate_python(draft, "HIDDEN_TESTS_DRAFT")

    HIDDEN_TESTS_DRAFT_PATH.write_text(
        draft,
        encoding="utf-8",
    )

    print(
        f"[TEST DESIGNER] wrote "
        f"{HIDDEN_TESTS_DRAFT_PATH}"
    )

    return draft

def audit_hidden_tests(
    client: OpenAI,
    draft_tests: str,
) -> str:
    print("[TEST AUDITOR] auditing hidden tests...")

    auditor_input = (
        "TASK SPECIFICATION:\n"
        f"{TASK}\n\n"
        "DRAFT HIDDEN TEST SUITE:\n"
        f"{draft_tests}\n\n"
        "Audit this suite and return the final executable "
        "hidden test suite."
    )

    audited_tests = strip_fences(
        call_role(
            client,
            TEST_AUDITOR_SYSTEM,
            auditor_input,
        )
    )

    validate_python(
        audited_tests,
        "HIDDEN_TESTS",
    )

    HIDDEN_TESTS_PATH.write_text(
        audited_tests,
        encoding="utf-8",
    )

    if audited_tests.strip() == draft_tests.strip():
        print(
            "[TEST AUDITOR] approved draft without changes"
        )
    else:
        print(
            "[TEST AUDITOR] revised test suite"
        )

    print(
        f"[TEST AUDITOR] wrote {HIDDEN_TESTS_PATH}"
    )

    return audited_tests

def decode_stream(stream) -> str:
    if stream is None:
        return ""
    if isinstance(stream, bytes):
        return stream.decode("utf-8", "replace")
    return stream


def format_timeout(
    exc: subprocess.TimeoutExpired,
) -> str:
    captured = (
        decode_stream(exc.stdout)
        + decode_stream(exc.stderr)
    ).strip()

    message = (
        f"[TIMEOUT] candidate did not finish within "
        f"{RUN_TIMEOUT}s and was terminated"
    )

    if captured:
        return f"{captured}\n{message}"

    return message


def run_candidate(
    hidden_tests: str,
) -> tuple[int, str]:

    TEST_FILE.write_text(
        hidden_tests,
        encoding="utf-8",
    )

    try:
        proc = subprocess.run(
            [sys.executable, str(TEST_FILE.name)],
            cwd=WORKDIR,
            text=True,
            capture_output=True,
            timeout=RUN_TIMEOUT,
        )
    except subprocess.TimeoutExpired as exc:
        return 1, format_timeout(exc)
    finally:
        # The next Solver pass runs here and must never see the tests.
        TEST_FILE.unlink(missing_ok=True)

    output = (
        proc.stdout
        + ("\n" if proc.stdout and proc.stderr else "")
        + proc.stderr
    ).strip()

    return proc.returncode, output


def main() -> int:
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=BASE_URL or None,
    )

    WORKDIR.mkdir(parents=True, exist_ok=True)

    print(f"[SWARM] model={MODEL} max_iters={MAX_ITERS}")
    print(
        "[SWARM] infrastructure: "
        "Test Designer -> Test Auditor -> "
        "Solver -> Runner -> Verifier"
    )

    # Phase 1: build independent verification
    draft_tests = generate_hidden_tests(client)

    # Phase 2: audit verification itself
    hidden_tests = audit_hidden_tests(
        client,
        draft_tests,
    )

    # Phase 3: solve
    feedback = (
        "No prior feedback. "
        "Produce the first implementation."
    )

    start = time.time()

    for iteration in range(1, MAX_ITERS + 1):
        print(
            f"\n=== ITERATION "
            f"{iteration}/{MAX_ITERS} ==="
        )

        solver_input = (
            f"SPECIFICATION:\n{TASK}\n\n"
            f"FEEDBACK FROM VERIFIER:\n{feedback}"
        )

        source = strip_fences(
            call_role(
                client,
                SOLVER_SYSTEM,
                solver_input,
            )
        )

        CANDIDATE.write_text(
            source,
            encoding="utf-8",
        )

        print(
            f"[SOLVER] wrote {CANDIDATE} "
            f"({len(source)} chars)"
        )

        code, runner_output = run_candidate(
            hidden_tests
        )

        print("[RUNNER]")
        print(
            textwrap.indent(
                runner_output or "(no output)",
                "  ",
            )
        )

        if (
            code == 0
            and "[VERIFIED]" in runner_output
        ):
            elapsed = time.time() - start

            print(
                f"\n[VERIFIED] candidate accepted "
                f"after {iteration} iteration(s) "
                f"in {elapsed:.1f}s"
            )

            print(f"[ARTIFACT] {CANDIDATE}")
            return 0

        verifier_input = (
            f"SPECIFICATION:\n{TASK}\n\n"
            f"CANDIDATE SOURCE:\n{source}\n\n"
            f"RUNNER OUTPUT:\n{runner_output}"
        )

        feedback = call_role(
            client,
            VERIFIER_SYSTEM,
            verifier_input,
        )

        print("[VERIFIER/CRITIC]")
        print(
            textwrap.indent(
                feedback,
                "  ",
            )
        )

    print(
        "\n[FAILED] iteration budget exhausted; "
        "inspect .swarm_run/candidate.py"
    )

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
