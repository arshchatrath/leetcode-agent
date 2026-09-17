"""Wraps the Claude Code CLI (headless) to generate approach + code for a problem."""
import re
import subprocess

from leetcode_client import Question

RESPONSE_FORMAT = """Respond in exactly this format, nothing else:

### APPROACH
<1-3 sentence intuition>

### CODE
```python
<complete solution, matching the given function signature exactly>
```"""


def build_initial_prompt(question: Question) -> str:
    return (
        f"Solve this LeetCode problem in Python 3.\n\n"
        f"Title: {question.title} ({question.difficulty})\n\n"
        f"{question.content}\n\n"
        f"Starter code:\n```python\n{question.python3_stub}\n```\n\n"
        f"{RESPONSE_FORMAT}"
    )


def build_retry_prompt(question: Question, previous_code: str, verdict: dict) -> str:
    detail_lines = []
    for key in ("status_msg", "runtime_error", "compile_error", "full_compile_error",
                "last_testcase", "expected_output", "code_output"):
        value = verdict.get(key)
        if value:
            detail_lines.append(f"{key}: {value}")
    detail = "\n".join(detail_lines)
    return (
        f"Your previous solution to this LeetCode problem failed the judge. Fix it.\n\n"
        f"Title: {question.title} ({question.difficulty})\n\n"
        f"{question.content}\n\n"
        f"Previous code:\n```python\n{previous_code}\n```\n\n"
        f"Judge feedback:\n{detail}\n\n"
        f"{RESPONSE_FORMAT}"
    )


def run_claude(prompt: str) -> str:
    # NOTE: verify the non-interactive flag with `claude --help` for your
    # installed version before relying on -p; this is the only place the
    # CLI is invoked, so adjust here if the flag/output shape differs.
    result = subprocess.run(
        ["claude", "-p", prompt], capture_output=True, text=True, timeout=180
    )
    return result.stdout


def parse_response(text: str) -> tuple:
    approach_match = re.search(r"###\s*APPROACH\s*\n(.*?)(?=###\s*CODE)", text, re.DOTALL)
    code_match = re.search(r"```python\s*\n(.*?)```", text, re.DOTALL)
    if not approach_match or not code_match:
        raise ValueError("could not parse claude response")
    return approach_match.group(1).strip(), code_match.group(1).strip()


def solve(question: Question, previous_code: str = None, verdict: dict = None) -> tuple:
    if previous_code is None:
        prompt = build_initial_prompt(question)
    else:
        prompt = build_retry_prompt(question, previous_code, verdict or {})
    return parse_response(run_claude(prompt))


def demo():
    fixture = (
        "### APPROACH\nUse a hash map to track seen values.\n\n"
        "### CODE\n```python\nclass Solution:\n    def f(self):\n        pass\n```\n"
    )
    approach, code = parse_response(fixture)
    assert approach == "Use a hash map to track seen values."
    assert "class Solution" in code
    try:
        parse_response("no markers here")
        assert False, "expected ValueError"
    except ValueError:
        pass
    print("solver.py self-check OK")


if __name__ == "__main__":
    demo()
