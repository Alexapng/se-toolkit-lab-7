"""LLM client with tool-based intent routing."""

from __future__ import annotations

import json
import sys
from typing import Any

import httpx

from config import BotConfig

# ---------------------------------------------------------------------------
# Tool definitions — the LLM reads these descriptions to decide what to call.
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_items",
            "description": "List all labs, tasks, and other items available in the LMS.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_learners",
            "description": "List enrolled students with their groups and enrollment status.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_scores",
            "description": "Get score distribution across 4 buckets (0-25, 25-50, 50-75, 75-100) for a specific lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01', 'lab-04'.",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pass_rates",
            "description": "Get per-task average scores and attempt counts for a specific lab. Use this to compare task difficulty within a lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01', 'lab-04'.",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_timeline",
            "description": "Get daily submission counts for a specific lab. Use this to see activity patterns over time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01'.",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_groups",
            "description": "Get per-group average scores and student counts for a specific lab. Use this to compare group performance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01'.",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_learners",
            "description": "Get top N learners by score for a specific lab. Use this for leaderboards and best-student queries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01'.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of top learners to return, default 5.",
                    },
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_completion_rate",
            "description": "Get overall completion rate percentage for a specific lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01'.",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_sync",
            "description": "Trigger the ETL pipeline to sync fresh data from the autochecker. Use this when the user asks to refresh or sync data.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]

SYSTEM_PROMPT = (
    "You are an LMS assistant. The user asks questions about labs, students, "
    "and analytics. You have tools to fetch data from the backend. ALWAYS call "
    "tools when the user's question requires data — do NOT guess or say "
    "\"I don't have that information\" if you can call a tool.\n\n"
    "When you need data, call the appropriate tool(s). After receiving tool "
    "results, produce a clear, formatted answer using the actual numbers.\n\n"
    "If the user sends a greeting, respond briefly and mention what you can help with.\n"
    "If the user message is unclear or ambiguous, ask a clarifying question.\n"
    "If the user message is gibberish, respond politely and list what you can do."
)


class LlmError(RuntimeError):
    """LLM service failure with user-facing details."""


class LlmClient:
    """OpenAI-compatible client for tool-calling with the LLM."""

    def __init__(self, config: BotConfig) -> None:
        self._base_url = config.llm_api_base_url.rstrip("/")
        self._api_key = config.llm_api_key
        self._model = getattr(config, "llm_api_model", None) or "coder-model"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def route(
        self,
        user_message: str,
        *,
        api_client: Any,  # LmsApiClient — used by tool callbacks
    ) -> str:
        """Run the tool-calling loop: LLM → execute tools → feed back → summarize."""
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        max_iterations = 10
        for _ in range(max_iterations):
            response = self._chat(messages, tools=TOOL_DEFINITIONS)

            # Check if the LLM made tool calls
            tool_calls = self._extract_tool_calls(response)
            if not tool_calls:
                # No tool calls — the LLM gave a final answer (or fallback)
                text = self._extract_text(response)
                if text:
                    return text
                # LLM returned neither text nor tool calls — shouldn't happen
                return "I received an empty response from the AI service. Please try again."

            # Log tool calls to stderr for debugging
            for tc in tool_calls:
                fname = tc.get("function", {}).get("name", "?")
                fargs = tc.get("function", {}).get("arguments", "{}")
                print(
                    f"[tool] LLM called: {fname}({fargs})",
                    file=sys.stderr,
                )

            # Execute each tool call and build results
            tool_results: list[tuple[dict[str, Any], str]] = []
            for tc in tool_calls:
                call_id = tc["id"]
                func_name = tc["function"]["name"]
                func_args = json.loads(tc["function"]["arguments"])

                result = self._execute_tool(func_name, func_args, api_client)
                result_str = json.dumps(result, ensure_ascii=False, default=str)
                print(
                    f"[tool] Result: {result_str[:150]}",
                    file=sys.stderr,
                )
                tool_results.append(
                    ({"role": "tool", "tool_call_id": call_id}, result_str)
                )

            # Feed tool results back into the conversation
            print(
                f"[summary] Feeding {len(tool_results)} tool result(s) back to LLM",
                file=sys.stderr,
            )
            for role_meta, content in tool_results:
                messages.append({**role_meta, "content": content})

        # If we exhausted iterations without a non-tool response
        return (
            "I gathered data but couldn't produce a final answer. "
            "Please try rephrasing your question."
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Send a chat-completion request and return the parsed JSON."""
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=60.0)
        except httpx.ConnectError as exc:
            raise LlmError(f"LLM service unavailable: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise LlmError(f"LLM request timed out: {exc}") from exc

        if resp.status_code >= 400:
            raise LlmError(
                f"LLM error: HTTP {resp.status_code} {resp.text[:200]}"
            )

        return resp.json()

    @staticmethod
    def _extract_tool_calls(response: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract tool_calls array from an LLM response."""
        # OpenAI-compatible format: choices[0].message.tool_calls
        choices = response.get("choices", [])
        if not choices:
            return []
        message = choices[0].get("message", {})
        return message.get("tool_calls") or []

    @staticmethod
    def _extract_text(response: dict[str, Any]) -> str:
        """Extract the text content from an LLM response."""
        choices = response.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        return message.get("content", "") or ""

    @staticmethod
    def _execute_tool(
        name: str, args: dict[str, Any], api_client: Any
    ) -> Any:
        """Dispatch a tool call to the corresponding API method."""
        dispatch = {
            "get_items": lambda: api_client.get_items(),
            "get_learners": lambda: api_client.get_learners(),
            "get_scores": lambda: api_client.get_scores(args["lab"]),
            "get_pass_rates": lambda: api_client.get_pass_rates(args["lab"]),
            "get_timeline": lambda: api_client.get_timeline(args["lab"]),
            "get_groups": lambda: api_client.get_groups(args["lab"]),
            "get_top_learners": lambda: api_client.get_top_learners(
                args["lab"], args.get("limit", 5)
            ),
            "get_completion_rate": lambda: api_client.get_completion_rate(
                args["lab"]
            ),
            "trigger_sync": lambda: api_client.trigger_sync(),
        }
        handler = dispatch.get(name)
        if handler is None:
            return {"error": f"Unknown tool: {name}"}
        return handler()
