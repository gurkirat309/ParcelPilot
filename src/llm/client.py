"""The ONLY module that talks to an LLM provider (Rule 2).

Exposes a provider-neutral `chat(messages, tools)` returning a normalized
`LLMResponse` (assistant text and/or tool calls). Gemini and Groq are both
supported behind one interface; the active provider is env-selected, with an
optional automatic fallback. Embeddings are NOT here — they are always local.

Neutral message shapes (list of dicts):
  {"role": "system"|"user", "content": str}
  {"role": "assistant", "content": str|None, "tool_calls": [ToolCall...]}
  {"role": "tool", "tool_call_id": str, "name": str, "content": str}
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from src.config import get_settings


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict  # JSON-schema object: {"type":"object","properties":{...},"required":[...]}


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    args: dict
    # Opaque provider state that must be replayed. Gemini 3.x "thinking" models
    # attach a thought_signature to each function_call part and reject history
    # that omits it. Ignored by Groq.
    signature: bytes | None = None


@dataclass
class LLMResponse:
    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    provider: str = ""


# --- Groq (OpenAI-compatible) -------------------------------------------------

class GroqClient:
    name = "groq"

    def __init__(self) -> None:
        from groq import Groq

        s = get_settings()
        self._client = Groq(api_key=s.groq_api_key)
        self._model = s.groq_model

    def _tools(self, tools: list[ToolSpec]) -> list[dict]:
        return [
            {"type": "function",
             "function": {"name": t.name, "description": t.description,
                          "parameters": t.parameters}}
            for t in tools
        ]

    def _messages(self, messages: list[dict]) -> list[dict]:
        out: list[dict] = []
        for m in messages:
            if m["role"] == "assistant" and m.get("tool_calls"):
                out.append({
                    "role": "assistant",
                    "content": m.get("content") or "",
                    "tool_calls": [
                        {"id": tc.id, "type": "function",
                         "function": {"name": tc.name, "arguments": json.dumps(tc.args)}}
                        for tc in m["tool_calls"]
                    ],
                })
            elif m["role"] == "tool":
                out.append({"role": "tool", "tool_call_id": m["tool_call_id"],
                            "content": m["content"]})
            else:
                out.append({"role": m["role"], "content": m.get("content") or ""})
        return out

    def chat(self, messages: list[dict], tools: list[ToolSpec] | None) -> LLMResponse:
        kwargs: dict = {"model": self._model, "messages": self._messages(messages),
                        "temperature": 0}
        if tools:
            kwargs["tools"] = self._tools(tools)
            kwargs["tool_choice"] = "auto"
        resp = self._client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        calls = [
            ToolCall(tc.id, tc.function.name, json.loads(tc.function.arguments or "{}"))
            for tc in (msg.tool_calls or [])
        ]
        return LLMResponse(msg.content, calls, self.name)


# --- Gemini (google-genai) ----------------------------------------------------

_GENAI_TYPE = {"string": "STRING", "integer": "INTEGER", "number": "NUMBER",
               "boolean": "BOOLEAN", "object": "OBJECT", "array": "ARRAY"}


class GeminiClient:
    name = "gemini"

    def __init__(self) -> None:
        from google import genai

        s = get_settings()
        self._genai = genai
        from google.genai import types

        self._types = types
        self._client = genai.Client(api_key=s.gemini_api_key)
        self._model = s.gemini_model

    def _schema(self, js: dict):
        t = self._types
        props = {
            k: t.Schema(type=_GENAI_TYPE.get(v.get("type", "string"), "STRING"),
                        description=v.get("description", ""),
                        enum=v.get("enum"))
            for k, v in js.get("properties", {}).items()
        }
        return t.Schema(type="OBJECT", properties=props or None,
                        required=js.get("required") or None)

    def _tools(self, tools: list[ToolSpec]):
        t = self._types
        decls = [t.FunctionDeclaration(name=s.name, description=s.description,
                                       parameters=self._schema(s.parameters))
                 for s in tools]
        return [t.Tool(function_declarations=decls)]

    def _contents(self, messages: list[dict]):
        t = self._types
        contents = []
        for m in messages:
            if m["role"] == "system":
                continue  # handled as system_instruction
            if m["role"] == "user":
                contents.append(t.Content(role="user",
                                          parts=[t.Part.from_text(text=m["content"])]))
            elif m["role"] == "assistant":
                parts = []
                if m.get("content"):
                    parts.append(t.Part.from_text(text=m["content"]))
                for tc in m.get("tool_calls", []):
                    parts.append(t.Part(
                        function_call=t.FunctionCall(name=tc.name, args=tc.args),
                        thought_signature=tc.signature))
                contents.append(t.Content(role="model", parts=parts))
            elif m["role"] == "tool":
                contents.append(t.Content(role="user", parts=[
                    t.Part.from_function_response(
                        name=m["name"], response={"result": m["content"]})]))
        return contents

    def chat(self, messages: list[dict], tools: list[ToolSpec] | None) -> LLMResponse:
        t = self._types
        system = next((m["content"] for m in messages if m["role"] == "system"), None)
        cfg = t.GenerateContentConfig(
            system_instruction=system,
            temperature=0,
            tools=self._tools(tools) if tools else None,
            automatic_function_calling=t.AutomaticFunctionCallingConfig(disable=True),
        )
        resp = self._client.models.generate_content(
            model=self._model, contents=self._contents(messages), config=cfg)

        text_parts, calls = [], []
        cand = resp.candidates[0] if resp.candidates else None
        for i, part in enumerate(getattr(cand.content, "parts", []) or []) if cand else []:
            if getattr(part, "function_call", None):
                fc = part.function_call
                calls.append(ToolCall(f"call_{i}", fc.name, dict(fc.args or {}),
                                      getattr(part, "thought_signature", None)))
            elif getattr(part, "text", None):
                text_parts.append(part.text)
        return LLMResponse("".join(text_parts) or None, calls, self.name)


# --- Factory + fallback -------------------------------------------------------

def _make(provider: str):
    if provider == "gemini":
        return GeminiClient()
    if provider == "groq":
        return GroqClient()
    raise ValueError(f"Unknown provider: {provider!r}")


class LLMClient:
    """Primary provider with optional automatic fallback on error."""

    def __init__(self) -> None:
        s = get_settings()
        self._primary = _make(s.llm_provider)
        self._fallback = _make(s.llm_fallback_provider) if s.llm_fallback_provider else None

    def chat(self, messages: list[dict], tools: list[ToolSpec] | None = None) -> LLMResponse:
        try:
            return self._primary.chat(messages, tools)
        except Exception:
            if self._fallback is None:
                raise
            return self._fallback.chat(messages, tools)
