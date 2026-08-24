"""Hand-written tool-calling agent loop (Rule 8: no frameworks).

Capped at `max_agent_iterations` (Rule 1). Emits a step-by-step trace of tool
calls for the UI. The model chooses tools; the code executes them, enforces
scope/precedence in the tools, and never lets the model do the math itself.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field

from src.config import get_settings
from src.data.repository import Repository, Session
from src.llm.client import LLMClient

from .tools import AgentContext, execute_tool, tools_for

_PRECEDENCE = (
    "SOURCE PRECEDENCE (highest wins):\n"
    "1. The caller's OWN customer agreement (only their account's contract).\n"
    "2. Current global policy / SOP (Support Policy v3, Cancellation & Credit SOP v4).\n"
    "3. Product Operations Guide / known issues.\n"
    "4. Historical ticket resolutions — CONTEXT ONLY; may be WRONG; NEVER cite as a basis.\n"
    "5. Deprecated docs (Support Policy v2) — excluded unless the user asks what changed.\n"
)

_RULES = (
    "RULES:\n"
    "- Use tools; never guess. If something is not in the sources, say so and escalate.\n"
    "- For ANY fee, credit, SLA, or eligibility question, call the matching calc_* tool "
    "and report its result. Never do the arithmetic or decide eligibility yourself.\n"
    "- Resolve conflicts with the precedence above. State which source governs and cite "
    "it (file + page). If a historical resolution contradicts a higher source, follow the "
    "higher source and note the discrepancy.\n"
    "- State-changing actions (escalation, ticket update, follow-up task) are PROPOSALS: "
    "call the create_/update_ tool to prepare one, then ask the user to confirm. Never "
    "claim an action is done.\n"
    "- If a calculation returns needs_verification / not computable, do not promise an "
    "outcome — explain what is missing and offer to escalate.\n"
    "- Be concise. Cite sources for policy claims.\n"
)

_CUSTOMER = (
    "You are ParcelPilot's customer support agent. You are talking to an authenticated "
    "customer who can only see their own account's data. Be helpful and clear.\n"
)
_INTERNAL = (
    "You are ParcelPilot's internal support/operations assistant for authorised staff. "
    "You can read across accounts and help investigate, prioritise, and act on issues.\n"
)


def system_prompt(session: Session) -> str:
    persona = _INTERNAL if session.is_internal else _CUSTOMER
    scope = ("" if session.is_internal
             else f"The customer's account_id is {session.account_id} (already applied "
                  "server-side; never ask for it).\n")
    return persona + scope + "\n" + _PRECEDENCE + "\n" + _RULES


@dataclass
class TraceStep:
    tool: str
    args: dict
    result: str


@dataclass
class AgentResult:
    answer: str
    trace: list[TraceStep] = field(default_factory=list)
    iterations: int = 0
    provider: str = ""


def iter_agent(session: Session, user_message: str, *,
               repo: Repository | None = None,
               history: list[dict] | None = None) -> Iterator[dict]:
    """Core loop as an event stream. Yields:
      {"type":"tool_call","tool","args"}
      {"type":"tool_result","tool","result"(parsed)}
      {"type":"final","answer","iterations","provider"}
    """
    from src.retrieval.index import get_index

    ctx = AgentContext(session, repo or Repository(), get_index())
    tools = tools_for(session)
    llm = LLMClient()
    max_iter = get_settings().max_agent_iterations

    messages: list[dict] = [{"role": "system", "content": system_prompt(session)}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    provider = ""
    for i in range(1, max_iter + 1):
        resp = llm.chat(messages, tools)
        provider = resp.provider
        if not resp.tool_calls:
            yield {"type": "final", "answer": resp.text or "",
                   "iterations": i, "provider": provider}
            return

        messages.append({"role": "assistant", "content": resp.text,
                         "tool_calls": resp.tool_calls})
        for tc in resp.tool_calls:
            yield {"type": "tool_call", "tool": tc.name, "args": tc.args}
            result = execute_tool(tc.name, tc.args, ctx)
            yield {"type": "tool_result", "tool": tc.name, "result": _parse(result)}
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "name": tc.name, "content": result})

    final = llm.chat(messages + [{"role": "user",
                     "content": "Summarise your answer now from what you have."}], None)
    yield {"type": "final", "answer": final.text or "(no answer)",
           "iterations": max_iter, "provider": provider}


def run_agent(session: Session, user_message: str, *,
              repo: Repository | None = None,
              history: list[dict] | None = None) -> AgentResult:
    """Collect the event stream into a single result (non-streaming callers/tests)."""
    trace: list[TraceStep] = []
    answer, iterations, provider = "", 0, ""
    pending: dict | None = None
    for ev in iter_agent(session, user_message, repo=repo, history=history):
        if ev["type"] == "tool_call":
            pending = ev
        elif ev["type"] == "tool_result":
            trace.append(TraceStep(ev["tool"], pending["args"] if pending else {},
                                   json.dumps(ev["result"])))
            pending = None
        elif ev["type"] == "final":
            answer, iterations, provider = ev["answer"], ev["iterations"], ev["provider"]
    return AgentResult(answer, trace, iterations, provider)


def _parse(result: str) -> dict:
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return {"raw": result}
