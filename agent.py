"""
Agent — Wraps a Claude model with a system prompt and a set of tools,
providing a simple `run()` interface for agentic task execution.
"""

from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Optional
import anthropic

from .tool import Tool


class AgentResult:
    """The result of an agent run."""

    def __init__(
        self,
        output: str,
        tool_calls: List[Dict[str, Any]],
        iterations: int,
        usage: Optional[Dict[str, int]] = None,
    ):
        self.output = output
        self.tool_calls = tool_calls
        self.iterations = iterations
        self.usage = usage or {}

    def __str__(self) -> str:
        return self.output

    def __repr__(self) -> str:
        return (
            f"AgentResult(iterations={self.iterations}, "
            f"tool_calls={len(self.tool_calls)}, "
            f"output_len={len(self.output)})"
        )


class Agent:
    """
    An AI agent powered by Claude that can use a set of registered tools
    to complete multi-step tasks.

    Usage:
        agent = Agent(
            name="ResearchAgent",
            description="Researches topics and summarises findings",
            system_prompt="You are a research assistant ...",
            tools=[search_tool, summarise_tool],
            api_key="sk-ant-...",
        )
        result = agent.run("What is quantum entanglement?")
        print(result.output)
    """

    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    MAX_ITERATIONS = 10

    def __init__(
        self,
        name: str,
        description: str,
        system_prompt: str,
        tools: Optional[List[Tool]] = None,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        max_iterations: int = MAX_ITERATIONS,
        max_tokens: int = 4096,
        owner_id: Optional[str] = None,
        category: str = "general",
        tags: Optional[List[str]] = None,
    ):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.tools: List[Tool] = tools or []
        self.model = model
        self.max_iterations = max_iterations
        self.max_tokens = max_tokens
        self.owner_id = owner_id
        self.category = category
        self.tags: List[str] = tags or []

        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._client = anthropic.Anthropic(api_key=api_key)
        self._tool_map: Dict[str, Tool] = {t.name: t for t in self.tools}
        self._run_count = 0

    # ------------------------------------------------------------------
    # Tool management
    # ------------------------------------------------------------------

    def add_tool(self, tool: Tool) -> None:
        """Register an additional tool on this agent."""
        if len(self.tools) >= 5:
            raise ValueError("An agent may use at most 5 tools.")
        self.tools.append(tool)
        self._tool_map[tool.name] = tool

    def remove_tool(self, tool_name: str) -> bool:
        tool = self._tool_map.pop(tool_name, None)
        if tool:
            self.tools = [t for t in self.tools if t.name != tool_name]
            return True
        return False

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run(self, user_message: str, context: Optional[str] = None) -> AgentResult:
        """
        Run the agent with a user message, executing tools as needed until
        a final response is produced or max_iterations is reached.
        """
        self._run_count += 1
        messages: List[Dict[str, Any]] = []

        if context:
            messages.append({"role": "user", "content": context})
            messages.append({"role": "assistant", "content": "Understood. Ready to help."})

        messages.append({"role": "user", "content": user_message})

        tool_schemas = [t.to_claude_schema() for t in self.tools]
        all_tool_calls: List[Dict[str, Any]] = []
        total_usage: Dict[str, int] = {}
        iterations = 0

        while iterations < self.max_iterations:
            iterations += 1
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "system": self.system_prompt,
                "messages": messages,
            }
            if tool_schemas:
                kwargs["tools"] = tool_schemas

            response = self._client.messages.create(**kwargs)

            # Accumulate token usage
            if hasattr(response, "usage"):
                for key in ("input_tokens", "output_tokens"):
                    val = getattr(response.usage, key, 0)
                    total_usage[key] = total_usage.get(key, 0) + val

            # Check stop reason
            if response.stop_reason == "end_turn":
                final_text = self._extract_text(response)
                return AgentResult(
                    output=final_text,
                    tool_calls=all_tool_calls,
                    iterations=iterations,
                    usage=total_usage,
                )

            if response.stop_reason == "tool_use":
                # Build assistant turn from current response blocks
                assistant_content = [b.model_dump() for b in response.content]
                messages.append({"role": "assistant", "content": assistant_content})

                # Execute each tool call and collect results
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        tool_id = block.id

                        tool_record = {
                            "tool": tool_name,
                            "input": tool_input,
                            "iteration": iterations,
                        }

                        if tool_name in self._tool_map:
                            try:
                                result = self._tool_map[tool_name].execute(tool_input)
                                tool_record["result"] = str(result)
                                tool_record["error"] = None
                                content = str(result)
                            except Exception as exc:
                                tool_record["result"] = None
                                tool_record["error"] = str(exc)
                                content = f"Error executing tool: {exc}"
                        else:
                            content = f"Tool '{tool_name}' not found."
                            tool_record["error"] = content
                            tool_record["result"] = None

                        all_tool_calls.append(tool_record)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": content,
                        })

                messages.append({"role": "user", "content": tool_results})
                continue

            # Any other stop reason — return what we have
            break

        final_text = self._extract_text(response) if iterations > 0 else "Max iterations reached."
        return AgentResult(
            output=final_text,
            tool_calls=all_tool_calls,
            iterations=iterations,
            usage=total_usage,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(response: Any) -> str:
        parts = []
        for block in response.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "\n".join(parts).strip()

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "model": self.model,
            "max_iterations": self.max_iterations,
            "max_tokens": self.max_tokens,
            "owner_id": self.owner_id,
            "category": self.category,
            "tags": self.tags,
            "tools": [t.to_dict() for t in self.tools],
            "run_count": self._run_count,
        }

    def __repr__(self) -> str:
        return (
            f"Agent(name={self.name!r}, tools={len(self.tools)}, "
            f"model={self.model!r})"
        )
