"""Deterministic safety policy for agent tool attempts (no tool execution).

Classifies missing executables, workspace denials, syntax failures and repeated
attempts. A repeated failed call is blocked; only a changed strategy can proceed.
"""
from dataclasses import dataclass
import hashlib
import json

MAX_REPEATS = 2

@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    recommendation: str

def classify_failure(message: str) -> str:
    if not isinstance(message, str):
        return "unknown"
    s = message.casefold()
    if "path escapes the allowed workspace" in s:
        return "workspace_denied"
    if ("commandnotfoundexception" in s or "not recognized" in s or
            "no se reconoce" in s):
        return "missing_command"
    if "usage: git diff" in s or "git: usage:" in s:
        return "invalid_command"
    if "ran out of tokens" in s:
        return "token_budget"
    if "loop guard" in s:
        return "repeated_sequence"
    return "unknown"

RECOMMENDATIONS = {
    "workspace_denied": "Use an authorized workspace or request explicit access; do not retry the denied path.",
    "missing_command": "Check installed tools and select an available alternative; do not retry the missing executable.",
    "invalid_command": "Validate arguments and run one corrected command, not the identical failing command.",
    "token_budget": "Reduce task scope and context; reserve output tokens for tool calls.",
    "repeated_sequence": "Stop the repeated sequence and switch strategy or record a blocker.",
    "unknown": "Inspect the failure and change the approach before retrying.",
}

class RecoveryGuard:
    def __init__(self, max_repeats=MAX_REPEATS):
        if not isinstance(max_repeats, int) or max_repeats < 1:
            raise ValueError("max_repeats must be positive")
        self.max_repeats = max_repeats
        self.failures = {}

    @staticmethod
    def fingerprint(tool: str, arguments: dict) -> str:
        if not isinstance(tool, str) or not isinstance(arguments, dict):
            raise ValueError("Invalid tool call")
        # Hash only: no command arguments, paths or tokens retained in state.
        payload = json.dumps([tool, arguments], sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def check(self, tool: str, arguments: dict) -> Decision:
        key = self.fingerprint(tool, arguments)
        count = self.failures.get(key, 0)
        if count >= self.max_repeats:
            return Decision(False, "repeated_failed_call",
                            "Stop and choose a different, authorized strategy.")
        return Decision(True, "allowed", "")

    def record(self, tool: str, arguments: dict, *, succeeded: bool, error: str = "") -> Decision:
        key = self.fingerprint(tool, arguments)
        if succeeded:
            self.failures.pop(key, None)
            return Decision(True, "success", "")
        self.failures[key] = self.failures.get(key, 0) + 1
        category = classify_failure(error)
        return Decision(False, category, RECOMMENDATIONS[category])
